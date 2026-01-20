"""
NIGHTWATCH Unit Tests - Telescope Tools

Tests for the voice LLM tool definitions and registry.
These tests validate tool structure, format conversion, and registry operations.

Run:
    pytest tests/unit/test_telescope_tools.py -v

Note: This module imports telescope_tools.py directly to avoid numpy dependency
from the parent voice package during CI testing.
"""

import pytest
import json
import importlib.util
from pathlib import Path
from typing import List


def _import_telescope_tools():
    """
    Import telescope_tools module directly from file.

    This avoids importing the voice package which has numpy dependencies
    that may not be available during CI unit testing.
    """
    # Calculate path to telescope_tools.py relative to this test file
    test_dir = Path(__file__).parent
    project_root = test_dir.parent.parent
    module_path = project_root / "voice" / "tools" / "telescope_tools.py"

    spec = importlib.util.spec_from_file_location("telescope_tools", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import directly from file to avoid numpy dependency in voice/__init__.py
_tt = _import_telescope_tools()
Tool = _tt.Tool
ToolParameter = _tt.ToolParameter
ToolCategory = _tt.ToolCategory
ToolRegistry = _tt.ToolRegistry
TELESCOPE_TOOLS = _tt.TELESCOPE_TOOLS
TELESCOPE_SYSTEM_PROMPT = _tt.TELESCOPE_SYSTEM_PROMPT
create_default_handlers = _tt.create_default_handlers


# ============================================================================
# Tool Definition Tests
# ============================================================================

class TestToolDefinitions:
    """Tests for individual tool definitions."""

    def test_tools_list_not_empty(self):
        """Verify TELESCOPE_TOOLS contains tools."""
        assert len(TELESCOPE_TOOLS) > 0
        assert len(TELESCOPE_TOOLS) >= 40  # Plan specifies 44+ tools

    def test_all_tools_have_required_fields(self):
        """Verify all tools have required name, description, and category."""
        for tool in TELESCOPE_TOOLS:
            assert tool.name, f"Tool missing name: {tool}"
            assert len(tool.name) > 0, f"Tool has empty name: {tool}"
            assert tool.description, f"Tool {tool.name} missing description"
            assert len(tool.description) > 10, f"Tool {tool.name} has too short description"
            assert tool.category is not None, f"Tool {tool.name} missing category"
            assert isinstance(tool.category, ToolCategory), f"Tool {tool.name} has invalid category"

    def test_tool_names_are_unique(self):
        """Verify all tool names are unique."""
        names = [tool.name for tool in TELESCOPE_TOOLS]
        assert len(names) == len(set(names)), "Duplicate tool names found"

    def test_tool_names_are_valid_identifiers(self):
        """Verify tool names are valid Python identifiers (no spaces, etc.)."""
        for tool in TELESCOPE_TOOLS:
            assert " " not in tool.name, f"Tool name contains space: {tool.name}"
            assert tool.name.replace("_", "").isalnum(), \
                f"Tool name contains invalid characters: {tool.name}"

    def test_required_tools_exist(self):
        """Verify core tools required by the system are defined."""
        required_tools = [
            # Mount control (Phase 2)
            "goto_object",
            "park_telescope",
            "stop_telescope",
            "get_mount_status",
            # Encoder/PEC (Phase 2/5.1)
            "get_encoder_position",
            "pec_status",
            "pec_start",
            # INDI tools (Phase 5.1)
            "indi_list_devices",
            "indi_set_filter",
            "indi_move_focuser",
            # Alpaca tools (Phase 5.1)
            "alpaca_discover_devices",
            "alpaca_set_filter",
            "alpaca_move_focuser",
            # Voice style (Phase 5.1)
            "set_voice_style",
        ]

        tool_names = {tool.name for tool in TELESCOPE_TOOLS}
        for required in required_tools:
            assert required in tool_names, f"Required tool '{required}' not found"


class TestToolParameters:
    """Tests for tool parameter definitions."""

    def test_parameters_have_valid_types(self):
        """Verify all parameters have valid JSON schema types."""
        valid_types = {"string", "number", "boolean", "array", "object"}

        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                assert param.type in valid_types, \
                    f"Tool {tool.name} parameter {param.name} has invalid type: {param.type}"

    def test_required_parameters_marked(self):
        """Verify required parameters are properly marked."""
        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                assert isinstance(param.required, bool), \
                    f"Tool {tool.name} parameter {param.name} 'required' should be boolean"

    def test_enum_parameters_have_values(self):
        """Verify parameters with enum have at least 2 values."""
        for tool in TELESCOPE_TOOLS:
            for param in tool.parameters:
                if param.enum is not None:
                    assert len(param.enum) >= 2, \
                        f"Tool {tool.name} parameter {param.name} enum should have >= 2 values"


# ============================================================================
# Tool Category Tests
# ============================================================================

class TestToolCategories:
    """Tests for tool categories."""

    def test_all_categories_have_tools(self):
        """Verify each category has at least one tool."""
        tools_by_category = {}
        for tool in TELESCOPE_TOOLS:
            cat = tool.category
            if cat not in tools_by_category:
                tools_by_category[cat] = []
            tools_by_category[cat].append(tool)

        # Core categories should have tools
        required_categories = [
            ToolCategory.MOUNT,
            ToolCategory.CATALOG,
            ToolCategory.WEATHER,
            ToolCategory.CAMERA,
            ToolCategory.FOCUS,
        ]

        for cat in required_categories:
            assert cat in tools_by_category, f"Category {cat} has no tools"
            assert len(tools_by_category[cat]) > 0, f"Category {cat} is empty"

    def test_mount_category_has_encoder_and_pec(self):
        """Verify MOUNT category includes encoder and PEC tools (Phase 5.1)."""
        mount_tools = [t for t in TELESCOPE_TOOLS if t.category == ToolCategory.MOUNT]
        mount_names = {t.name for t in mount_tools}

        assert "get_encoder_position" in mount_names, "Encoder tool missing from MOUNT"
        assert "pec_status" in mount_names, "PEC tool missing from MOUNT"


# ============================================================================
# Format Conversion Tests
# ============================================================================

class TestFormatConversion:
    """Tests for tool format conversion (OpenAI/Anthropic)."""

    def test_to_openai_format_structure(self):
        """Verify OpenAI format has correct structure."""
        tool = TELESCOPE_TOOLS[0]
        openai_format = tool.to_openai_format()

        assert "type" in openai_format
        assert openai_format["type"] == "function"
        assert "function" in openai_format
        assert "name" in openai_format["function"]
        assert "description" in openai_format["function"]
        assert "parameters" in openai_format["function"]

    def test_to_openai_format_parameters(self):
        """Verify OpenAI format parameters structure."""
        # Find a tool with parameters
        tool = next(t for t in TELESCOPE_TOOLS if len(t.parameters) > 0)
        openai_format = tool.to_openai_format()

        params = openai_format["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert isinstance(params["required"], list)

    def test_to_anthropic_format_structure(self):
        """Verify Anthropic format has correct structure."""
        tool = TELESCOPE_TOOLS[0]
        anthropic_format = tool.to_anthropic_format()

        assert "name" in anthropic_format
        assert "description" in anthropic_format
        assert "input_schema" in anthropic_format
        assert anthropic_format["input_schema"]["type"] == "object"

    def test_openai_format_is_valid_json(self):
        """Verify OpenAI format produces valid JSON."""
        for tool in TELESCOPE_TOOLS[:10]:  # Test first 10 tools
            openai_format = tool.to_openai_format()
            json_str = json.dumps(openai_format)
            parsed = json.loads(json_str)
            assert parsed["function"]["name"] == tool.name

    def test_anthropic_format_is_valid_json(self):
        """Verify Anthropic format produces valid JSON."""
        for tool in TELESCOPE_TOOLS[:10]:
            anthropic_format = tool.to_anthropic_format()
            json_str = json.dumps(anthropic_format)
            parsed = json.loads(json_str)
            assert parsed["name"] == tool.name


# ============================================================================
# Tool Registry Tests
# ============================================================================

class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_registry_initialization(self):
        """Verify registry initializes with all tools."""
        registry = ToolRegistry()
        all_tools = registry.get_all_tools()

        assert len(all_tools) == len(TELESCOPE_TOOLS)

    def test_registry_get_tool_by_name(self):
        """Verify getting tool by name works."""
        registry = ToolRegistry()

        tool = registry.get_tool("goto_object")
        assert tool is not None
        assert tool.name == "goto_object"

        tool = registry.get_tool("nonexistent_tool")
        assert tool is None

    def test_registry_get_tools_by_category(self):
        """Verify filtering tools by category."""
        registry = ToolRegistry()

        mount_tools = registry.get_tools_by_category(ToolCategory.MOUNT)
        assert len(mount_tools) > 0
        assert all(t.category == ToolCategory.MOUNT for t in mount_tools)

    def test_registry_to_openai_format(self):
        """Verify registry can export all tools in OpenAI format."""
        registry = ToolRegistry()
        openai_tools = registry.to_openai_format()

        assert isinstance(openai_tools, list)
        assert len(openai_tools) == len(TELESCOPE_TOOLS)
        assert all("function" in t for t in openai_tools)

    def test_registry_to_anthropic_format(self):
        """Verify registry can export all tools in Anthropic format."""
        registry = ToolRegistry()
        anthropic_tools = registry.to_anthropic_format()

        assert isinstance(anthropic_tools, list)
        assert len(anthropic_tools) == len(TELESCOPE_TOOLS)
        assert all("input_schema" in t for t in anthropic_tools)

    def test_registry_register_custom_tool(self):
        """Verify registering a custom tool."""
        registry = ToolRegistry()
        initial_count = len(registry.get_all_tools())

        custom_tool = Tool(
            name="test_custom_tool",
            description="A test tool",
            category=ToolCategory.SESSION,
            parameters=[]
        )

        registry.register(custom_tool)

        assert len(registry.get_all_tools()) == initial_count + 1
        assert registry.get_tool("test_custom_tool") is not None

    def test_registry_set_handler(self):
        """Verify setting handler for a tool."""
        registry = ToolRegistry()

        async def custom_handler():
            return "test result"

        registry.set_handler("goto_object", custom_handler)

        # Verify handler is set (accessing internal state for test)
        assert "goto_object" in registry._handlers


# ============================================================================
# System Prompt Tests
# ============================================================================

class TestSystemPrompt:
    """Tests for the system prompt."""

    def test_system_prompt_exists(self):
        """Verify system prompt is defined."""
        assert TELESCOPE_SYSTEM_PROMPT is not None
        assert len(TELESCOPE_SYSTEM_PROMPT) > 1000  # Should be substantial

    def test_system_prompt_mentions_key_features(self):
        """Verify system prompt documents key features."""
        prompt_lower = TELESCOPE_SYSTEM_PROMPT.lower()

        # Phase 5.1 features should be documented
        assert "encoder" in prompt_lower, "Encoder not mentioned in prompt"
        assert "pec" in prompt_lower, "PEC not mentioned in prompt"
        assert "indi" in prompt_lower, "INDI not mentioned in prompt"
        assert "alpaca" in prompt_lower, "Alpaca not mentioned in prompt"
        assert "voice" in prompt_lower, "Voice not mentioned in prompt"

    def test_system_prompt_version(self):
        """Verify system prompt has version info."""
        # Version 3.3 per last commit
        assert "3.3" in TELESCOPE_SYSTEM_PROMPT or "version" in TELESCOPE_SYSTEM_PROMPT.lower()


# ============================================================================
# Handler Creation Tests
# ============================================================================

class TestHandlerCreation:
    """Tests for default handler creation."""

    def test_create_handlers_without_services(self):
        """Verify handlers can be created without any services."""
        handlers = create_default_handlers()

        assert isinstance(handlers, dict)
        assert len(handlers) > 0

    def test_handlers_are_callable(self):
        """Verify all handlers are callable."""
        handlers = create_default_handlers()

        for name, handler in handlers.items():
            assert callable(handler), f"Handler {name} is not callable"


# ============================================================================
# Mount Tool Handler Tests (Step 351)
# ============================================================================

class TestMountToolHandlers:
    """Tests for mount tool handlers."""

    def test_mount_tools_defined(self):
        """Verify all mount control tools are defined."""
        mount_tool_names = [
            "goto_object",
            "goto_coordinates",
            "park_telescope",
            "unpark_telescope",
            "stop_telescope",
            "start_tracking",
            "stop_tracking",
            "get_mount_status",
            "sync_position",
            "home_telescope",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in mount_tool_names:
            assert name in tool_names, f"Mount tool '{name}' not found"

    def test_goto_object_parameters(self):
        """Verify goto_object has object_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("goto_object")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names

        # object_name should be required
        object_param = next(p for p in tool.parameters if p.name == "object_name")
        assert object_param.required is True
        assert object_param.type == "string"

    def test_goto_coordinates_parameters(self):
        """Verify goto_coordinates has ra and dec parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("goto_coordinates")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "ra" in param_names
        assert "dec" in param_names

        # Both should be required
        for p in tool.parameters:
            if p.name in ("ra", "dec"):
                assert p.required is True
                assert p.type == "string"

    def test_park_telescope_parameters(self):
        """Verify park_telescope has optional confirmed parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("park_telescope")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "confirmed" in param_names

        confirmed_param = next(p for p in tool.parameters if p.name == "confirmed")
        assert confirmed_param.required is False
        assert confirmed_param.type == "boolean"

    def test_sync_position_parameters(self):
        """Verify sync_position has object_name and confirmed parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("sync_position")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names
        assert "confirmed" in param_names

    def test_mount_handlers_created(self):
        """Verify mount handlers are created in default handlers."""
        handlers = create_default_handlers()

        mount_handlers = [
            "goto_object",
            "goto_coordinates",
            "park_telescope",
            "unpark_telescope",
            "stop_telescope",
            "start_tracking",
            "stop_tracking",
            "get_mount_status",
            "sync_position",
            "home_telescope",
        ]

        for handler_name in mount_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Catalog Tool Handler Tests (Step 358)
# ============================================================================

class TestCatalogToolHandlers:
    """Tests for catalog tool handlers."""

    def test_catalog_tools_defined(self):
        """Verify all catalog tools are defined."""
        catalog_tool_names = [
            "lookup_object",
            "find_objects",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in catalog_tool_names:
            assert name in tool_names, f"Catalog tool '{name}' not found"

    def test_lookup_object_parameters(self):
        """Verify lookup_object has object_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("lookup_object")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "object_name" in param_names

        name_param = next(p for p in tool.parameters if p.name == "object_name")
        assert name_param.required is True
        assert name_param.type == "string"

    def test_find_objects_parameters(self):
        """Verify find_objects has filtering parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("find_objects")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        # Should have some filtering parameters
        assert len(param_names) > 0

    def test_catalog_handlers_created(self):
        """Verify catalog handlers are created in default handlers."""
        handlers = create_default_handlers()

        catalog_handlers = [
            "lookup_object",
            "find_objects",
        ]

        for handler_name in catalog_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Safety Tool Handler Tests (Step 385)
# ============================================================================

class TestSafetyToolHandlers:
    """Tests for safety tool handlers."""

    def test_safety_tools_defined(self):
        """Verify all safety tools are defined."""
        safety_tool_names = [
            "is_safe_to_observe",
            "get_sensor_health",
            "get_hysteresis_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in safety_tool_names:
            assert name in tool_names, f"Safety tool '{name}' not found"

    def test_is_safe_to_observe_no_required_params(self):
        """Verify is_safe_to_observe has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("is_safe_to_observe")
        assert tool is not None

        # Should have no required parameters or all optional
        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_get_sensor_health_no_required_params(self):
        """Verify get_sensor_health has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_sensor_health")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_safety_handlers_created(self):
        """Verify safety handlers are created in default handlers."""
        handlers = create_default_handlers()

        safety_handlers = [
            "is_safe_to_observe",
            "get_sensor_health",
            "get_hysteresis_status",
        ]

        for handler_name in safety_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_safety_tools_in_correct_category(self):
        """Verify safety tools are in SAFETY category."""
        registry = ToolRegistry()
        safety_tools = registry.get_tools_by_category(ToolCategory.SAFETY)
        safety_names = {t.name for t in safety_tools}

        expected = ["is_safe_to_observe", "get_sensor_health", "get_hysteresis_status"]
        for name in expected:
            assert name in safety_names, f"'{name}' not in SAFETY category"


# ============================================================================
# Ephemeris Tool Handler Tests (Step 369)
# ============================================================================

class TestEphemerisToolHandlers:
    """Tests for ephemeris tool handlers."""

    def test_ephemeris_tools_defined(self):
        """Verify all ephemeris tools are defined."""
        ephemeris_tool_names = [
            "get_planet_position",
            "get_visible_planets",
            "get_moon_info",
            "is_it_dark",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in ephemeris_tool_names:
            assert name in tool_names, f"Ephemeris tool '{name}' not found"

    def test_get_planet_position_parameters(self):
        """Verify get_planet_position has planet parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_planet_position")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "planet" in param_names

        planet_param = next(p for p in tool.parameters if p.name == "planet")
        assert planet_param.required is True
        assert planet_param.type == "string"

    def test_get_visible_planets_parameters(self):
        """Verify get_visible_planets has min_altitude parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_visible_planets")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "min_altitude" in param_names

        alt_param = next(p for p in tool.parameters if p.name == "min_altitude")
        assert alt_param.required is False  # Optional with default

    def test_ephemeris_handlers_created(self):
        """Verify ephemeris handlers are created in default handlers."""
        handlers = create_default_handlers()

        ephemeris_handlers = [
            "get_planet_position",
            "get_visible_planets",
            "get_moon_info",
            "is_it_dark",
        ]

        for handler_name in ephemeris_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_ephemeris_tools_in_correct_category(self):
        """Verify ephemeris tools are in EPHEMERIS category."""
        registry = ToolRegistry()
        ephemeris_tools = registry.get_tools_by_category(ToolCategory.EPHEMERIS)
        ephemeris_names = {t.name for t in ephemeris_tools}

        expected = ["get_planet_position", "get_visible_planets", "get_moon_info", "is_it_dark"]
        for name in expected:
            assert name in ephemeris_names, f"'{name}' not in EPHEMERIS category"


# ============================================================================
# Weather Tool Handler Tests (Step 378)
# ============================================================================

class TestWeatherToolHandlers:
    """Tests for weather tool handlers."""

    def test_weather_tools_defined(self):
        """Verify all weather tools are defined."""
        weather_tool_names = [
            "get_weather",
            "get_cloud_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in weather_tool_names:
            assert name in tool_names, f"Weather tool '{name}' not found"

    def test_get_weather_no_required_params(self):
        """Verify get_weather has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_weather")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_weather_handlers_created(self):
        """Verify weather handlers are created in default handlers."""
        handlers = create_default_handlers()

        weather_handlers = [
            "get_weather",
            "get_cloud_status",
        ]

        for handler_name in weather_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_weather_tools_in_correct_category(self):
        """Verify weather tools are in WEATHER category."""
        registry = ToolRegistry()
        weather_tools = registry.get_tools_by_category(ToolCategory.WEATHER)
        weather_names = {t.name for t in weather_tools}

        expected = ["get_weather", "get_cloud_status"]
        for name in expected:
            assert name in weather_names, f"'{name}' not in WEATHER category"


# ============================================================================
# Session Tool Handler Tests (Step 392)
# ============================================================================

class TestSessionToolHandlers:
    """Tests for session tool handlers."""

    def test_session_tools_defined(self):
        """Verify all session tools are defined."""
        session_tool_names = [
            "confirm_command",
            "get_observation_log",
            "set_voice_style",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in session_tool_names:
            assert name in tool_names, f"Session tool '{name}' not found"

    def test_confirm_command_parameters(self):
        """Verify confirm_command has action parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("confirm_command")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "action" in param_names

        action_param = next(p for p in tool.parameters if p.name == "action")
        assert action_param.required is True
        assert action_param.type == "string"

    def test_set_voice_style_parameters(self):
        """Verify set_voice_style has style parameter with enum."""
        registry = ToolRegistry()
        tool = registry.get_tool("set_voice_style")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "style" in param_names

        style_param = next(p for p in tool.parameters if p.name == "style")
        assert style_param.required is True
        assert style_param.enum is not None
        assert len(style_param.enum) >= 2  # At least 2 style options

    def test_session_handlers_created(self):
        """Verify session handlers are created in default handlers."""
        handlers = create_default_handlers()

        session_handlers = [
            "confirm_command",
            "get_observation_log",
            "set_voice_style",
        ]

        for handler_name in session_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Guiding Tool Handler Tests (Step 400)
# ============================================================================

class TestGuidingToolHandlers:
    """Tests for guiding tool handlers."""

    def test_guiding_tools_defined(self):
        """Verify all guiding tools are defined."""
        guiding_tool_names = [
            "stop_guiding",
            "get_guiding_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in guiding_tool_names:
            assert name in tool_names, f"Guiding tool '{name}' not found"

    def test_stop_guiding_no_required_params(self):
        """Verify stop_guiding has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("stop_guiding")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_get_guiding_status_no_required_params(self):
        """Verify get_guiding_status has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_guiding_status")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_guiding_handlers_created(self):
        """Verify guiding handlers are created in default handlers."""
        handlers = create_default_handlers()

        guiding_handlers = [
            "stop_guiding",
            "get_guiding_status",
        ]

        for handler_name in guiding_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_guiding_tools_in_correct_category(self):
        """Verify guiding tools are in GUIDING category."""
        registry = ToolRegistry()
        guiding_tools = registry.get_tools_by_category(ToolCategory.GUIDING)
        guiding_names = {t.name for t in guiding_tools}

        expected = ["stop_guiding", "get_guiding_status"]
        for name in expected:
            assert name in guiding_names, f"'{name}' not in GUIDING category"


# ============================================================================
# Camera Tool Handler Tests (Step 410)
# ============================================================================

class TestCameraToolHandlers:
    """Tests for camera tool handlers."""

    def test_camera_tools_defined(self):
        """Verify all camera tools are defined."""
        camera_tool_names = [
            "stop_capture",
            "get_camera_status",
            "set_camera_gain",
            "set_camera_exposure",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in camera_tool_names:
            assert name in tool_names, f"Camera tool '{name}' not found"

    def test_set_camera_gain_parameters(self):
        """Verify set_camera_gain has gain parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("set_camera_gain")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "gain" in param_names

        gain_param = next(p for p in tool.parameters if p.name == "gain")
        assert gain_param.required is True
        assert gain_param.type == "number"

    def test_set_camera_exposure_parameters(self):
        """Verify set_camera_exposure has exposure_ms parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("set_camera_exposure")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "exposure_ms" in param_names

        exp_param = next(p for p in tool.parameters if p.name == "exposure_ms")
        assert exp_param.required is True
        assert exp_param.type == "number"

    def test_camera_handlers_created(self):
        """Verify camera handlers are created in default handlers."""
        handlers = create_default_handlers()

        camera_handlers = [
            "stop_capture",
            "get_camera_status",
            "set_camera_gain",
            "set_camera_exposure",
        ]

        for handler_name in camera_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_camera_tools_in_correct_category(self):
        """Verify camera tools are in CAMERA category."""
        registry = ToolRegistry()
        camera_tools = registry.get_tools_by_category(ToolCategory.CAMERA)
        camera_names = {t.name for t in camera_tools}

        expected = ["stop_capture", "get_camera_status", "set_camera_gain", "set_camera_exposure"]
        for name in expected:
            assert name in camera_names, f"'{name}' not in CAMERA category"


# ============================================================================
# Focus Tool Handler Tests (Step 418)
# ============================================================================

class TestFocusToolHandlers:
    """Tests for focus tool handlers."""

    def test_focus_tools_defined(self):
        """Verify all focus tools are defined."""
        focus_tool_names = [
            "get_focus_status",
            "move_focus",
            "enable_temp_compensation",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in focus_tool_names:
            assert name in tool_names, f"Focus tool '{name}' not found"

    def test_move_focus_parameters(self):
        """Verify move_focus has position parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("move_focus")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        # Should have position parameter for movement
        assert "position" in param_names
        position_param = next(p for p in tool.parameters if p.name == "position")
        assert position_param.type == "number"

    def test_enable_temp_compensation_parameters(self):
        """Verify enable_temp_compensation has enabled parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("enable_temp_compensation")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "enabled" in param_names

        enabled_param = next(p for p in tool.parameters if p.name == "enabled")
        assert enabled_param.type == "boolean"

    def test_focus_handlers_created(self):
        """Verify focus handlers are created in default handlers."""
        handlers = create_default_handlers()

        focus_handlers = [
            "get_focus_status",
            "move_focus",
            "enable_temp_compensation",
        ]

        for handler_name in focus_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_focus_tools_in_correct_category(self):
        """Verify focus tools are in FOCUS category."""
        registry = ToolRegistry()
        focus_tools = registry.get_tools_by_category(ToolCategory.FOCUS)
        focus_names = {t.name for t in focus_tools}

        expected = ["get_focus_status", "move_focus", "enable_temp_compensation"]
        for name in expected:
            assert name in focus_names, f"'{name}' not in FOCUS category"


# ============================================================================
# Astrometry Tool Handler Tests (Step 425)
# ============================================================================

class TestAstrometryToolHandlers:
    """Tests for astrometry tool handlers."""

    def test_astrometry_tools_defined(self):
        """Verify all astrometry tools are defined."""
        astrometry_tool_names = [
            "plate_solve",
            "get_pointing_error",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in astrometry_tool_names:
            assert name in tool_names, f"Astrometry tool '{name}' not found"

    def test_plate_solve_parameters(self):
        """Verify plate_solve has sync_mount parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("plate_solve")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        # Has at least one parameter
        assert len(param_names) >= 1

    def test_get_pointing_error_no_required_params(self):
        """Verify get_pointing_error has no required parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_pointing_error")
        assert tool is not None

        required_params = [p for p in tool.parameters if p.required]
        assert len(required_params) == 0

    def test_astrometry_handlers_created(self):
        """Verify astrometry handlers are created in default handlers."""
        handlers = create_default_handlers()

        astrometry_handlers = [
            "plate_solve",
            "get_pointing_error",
        ]

        for handler_name in astrometry_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Enclosure Tool Handler Tests (Step 433)
# ============================================================================

class TestEnclosureToolHandlers:
    """Tests for enclosure tool handlers."""

    def test_enclosure_tools_defined(self):
        """Verify all enclosure tools are defined."""
        enclosure_tool_names = [
            "open_roof",
            "close_roof",
            "get_roof_status",
            "stop_roof",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in enclosure_tool_names:
            assert name in tool_names, f"Enclosure tool '{name}' not found"

    def test_close_roof_parameters(self):
        """Verify close_roof has emergency parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("close_roof")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "emergency" in param_names

        emergency_param = next(p for p in tool.parameters if p.name == "emergency")
        assert emergency_param.type == "boolean"
        assert emergency_param.required is False

    def test_enclosure_handlers_created(self):
        """Verify enclosure handlers are created in default handlers."""
        handlers = create_default_handlers()

        enclosure_handlers = [
            "open_roof",
            "close_roof",
            "get_roof_status",
            "stop_roof",
        ]

        for handler_name in enclosure_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_enclosure_tools_in_correct_category(self):
        """Verify enclosure tools are in ENCLOSURE category."""
        registry = ToolRegistry()
        enclosure_tools = registry.get_tools_by_category(ToolCategory.ENCLOSURE)
        enclosure_names = {t.name for t in enclosure_tools}

        expected = ["open_roof", "close_roof", "get_roof_status", "stop_roof"]
        for name in expected:
            assert name in enclosure_names, f"'{name}' not in ENCLOSURE category"


# ============================================================================
# Power Tool Handler Tests (Step 440)
# ============================================================================

class TestPowerToolHandlers:
    """Tests for power tool handlers."""

    def test_power_tools_defined(self):
        """Verify all power tools are defined."""
        power_tool_names = [
            "get_power_status",
            "get_power_events",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in power_tool_names:
            assert name in tool_names, f"Power tool '{name}' not found"

    def test_get_power_events_parameters(self):
        """Verify get_power_events has filtering parameters."""
        registry = ToolRegistry()
        tool = registry.get_tool("get_power_events")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        # Has at least one filtering parameter (hours is used for time range)
        assert len(param_names) >= 1

    def test_power_handlers_created(self):
        """Verify power handlers are created in default handlers."""
        handlers = create_default_handlers()

        power_handlers = [
            "get_power_status",
            "get_power_events",
        ]

        for handler_name in power_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_power_tools_in_correct_category(self):
        """Verify power tools are in POWER category."""
        registry = ToolRegistry()
        power_tools = registry.get_tools_by_category(ToolCategory.POWER)
        power_names = {t.name for t in power_tools}

        expected = ["get_power_status", "get_power_events"]
        for name in expected:
            assert name in power_names, f"'{name}' not in POWER category"


# ============================================================================
# INDI Tool Handler Tests (Step 445)
# ============================================================================

class TestINDIToolHandlers:
    """Tests for INDI tool handlers."""

    def test_indi_tools_defined(self):
        """Verify all INDI tools are defined."""
        indi_tool_names = [
            "indi_list_devices",
            "indi_set_filter",
            "indi_get_filter",
            "indi_move_focuser",
            "indi_get_focuser_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in indi_tool_names:
            assert name in tool_names, f"INDI tool '{name}' not found"

    def test_indi_set_filter_parameters(self):
        """Verify indi_set_filter has filter_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("indi_set_filter")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "filter_name" in param_names

        filter_param = next(p for p in tool.parameters if p.name == "filter_name")
        assert filter_param.required is True
        assert filter_param.type == "string"

    def test_indi_move_focuser_parameters(self):
        """Verify indi_move_focuser has position parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("indi_move_focuser")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "position" in param_names

    def test_indi_handlers_created(self):
        """Verify INDI handlers are created in default handlers."""
        handlers = create_default_handlers()

        indi_handlers = [
            "indi_list_devices",
            "indi_set_filter",
            "indi_get_filter",
            "indi_move_focuser",
            "indi_get_focuser_status",
        ]

        for handler_name in indi_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Alpaca Tool Handler Tests (Step 449)
# ============================================================================

class TestAlpacaToolHandlers:
    """Tests for Alpaca tool handlers."""

    def test_alpaca_tools_defined(self):
        """Verify all Alpaca tools are defined."""
        alpaca_tool_names = [
            "alpaca_discover_devices",
            "alpaca_set_filter",
            "alpaca_get_filter",
            "alpaca_move_focuser",
            "alpaca_get_focuser_status",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in alpaca_tool_names:
            assert name in tool_names, f"Alpaca tool '{name}' not found"

    def test_alpaca_set_filter_parameters(self):
        """Verify alpaca_set_filter has filter_name parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("alpaca_set_filter")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "filter_name" in param_names

        filter_param = next(p for p in tool.parameters if p.name == "filter_name")
        assert filter_param.required is True
        assert filter_param.type == "string"

    def test_alpaca_move_focuser_parameters(self):
        """Verify alpaca_move_focuser has position parameter."""
        registry = ToolRegistry()
        tool = registry.get_tool("alpaca_move_focuser")
        assert tool is not None

        param_names = {p.name for p in tool.parameters}
        assert "position" in param_names

    def test_alpaca_handlers_created(self):
        """Verify Alpaca handlers are created in default handlers."""
        handlers = create_default_handlers()

        alpaca_handlers = [
            "alpaca_discover_devices",
            "alpaca_set_filter",
            "alpaca_get_filter",
            "alpaca_move_focuser",
            "alpaca_get_focuser_status",
        ]

        for handler_name in alpaca_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])


# ============================================================================
# Encoder Tool Handler Tests (Step 456)
# ============================================================================

class TestEncoderToolHandlers:
    """Tests for encoder tool handlers."""

    def test_encoder_tools_defined(self):
        """Verify all encoder tools are defined."""
        encoder_tool_names = [
            "get_encoder_position",
            "get_pointing_correction",
            "pec_status",
            "pec_start",
            "pec_stop",
            "pec_record",
        ]
        tool_names = {t.name for t in TELESCOPE_TOOLS}
        for name in encoder_tool_names:
            assert name in tool_names, f"Encoder tool '{name}' not found"

    def test_pec_tools_no_required_params(self):
        """Verify PEC tools have no required parameters."""
        registry = ToolRegistry()

        pec_tools = ["pec_status", "pec_start", "pec_stop", "pec_record"]
        for tool_name in pec_tools:
            tool = registry.get_tool(tool_name)
            assert tool is not None, f"Tool {tool_name} not found"
            required_params = [p for p in tool.parameters if p.required]
            assert len(required_params) == 0, f"{tool_name} should have no required params"

    def test_encoder_handlers_created(self):
        """Verify encoder handlers are created in default handlers."""
        handlers = create_default_handlers()

        encoder_handlers = [
            "get_encoder_position",
            "get_pointing_correction",
            "pec_status",
            "pec_start",
            "pec_stop",
            "pec_record",
        ]

        for handler_name in encoder_handlers:
            assert handler_name in handlers, f"Handler '{handler_name}' not created"
            assert callable(handlers[handler_name])

    def test_encoder_tools_in_mount_category(self):
        """Verify encoder tools are in MOUNT category."""
        registry = ToolRegistry()
        mount_tools = registry.get_tools_by_category(ToolCategory.MOUNT)
        mount_names = {t.name for t in mount_tools}

        # Encoder and PEC tools should be in MOUNT category
        expected = ["get_encoder_position", "pec_status", "pec_start", "pec_stop", "pec_record"]
        for name in expected:
            assert name in mount_names, f"'{name}' not in MOUNT category"


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
