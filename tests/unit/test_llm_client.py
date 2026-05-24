"""
Unit tests for NIGHTWATCH LLM Client.

Tests LLM client functionality, backend selection, and token tracking.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest

from nightwatch.llm_client import (
    LLMClient,
    LLMBackend,
    LLMResponse,
    ToolCall,
    TokenUsage,
    ConversationMessage,
    MockLLMClient,
    OBSERVATORY_SYSTEM_PROMPT,
    create_llm_client,
)
from services.safety_monitor.monitor import (
    AlertLevel,
    SafetyAction,
    SafetyStatus,
)


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self):
        """Test default token counts."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.session_total_tokens == 0

    def test_add_tokens(self):
        """Test adding token counts."""
        usage = TokenUsage()
        usage.add(100, 50)

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.session_prompt_tokens == 100
        assert usage.session_completion_tokens == 50
        assert usage.session_total_tokens == 150

    def test_cumulative_tracking(self):
        """Test session token accumulation."""
        usage = TokenUsage()
        usage.add(100, 50)
        usage.add(200, 100)

        # Current request
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 100

        # Session totals
        assert usage.session_prompt_tokens == 300
        assert usage.session_completion_tokens == 150
        assert usage.session_total_tokens == 450

    def test_to_dict(self):
        """Test dictionary conversion."""
        usage = TokenUsage()
        usage.add(100, 50)

        d = usage.to_dict()
        assert d["prompt_tokens"] == 100
        assert d["completion_tokens"] == 50
        assert d["total_tokens"] == 150
        assert d["session_total_tokens"] == 150


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        tc = ToolCall(
            id="call_123",
            name="goto_object",
            arguments={"object_name": "M31"}
        )

        assert tc.id == "call_123"
        assert tc.name == "goto_object"
        assert tc.arguments["object_name"] == "M31"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "call_456",
            "name": "park_telescope",
            "arguments": {}
        }
        tc = ToolCall.from_dict(data)

        assert tc.id == "call_456"
        assert tc.name == "park_telescope"


class TestConversationMessage:
    """Tests for ConversationMessage dataclass."""

    def test_user_message(self):
        """Test creating user message."""
        msg = ConversationMessage(
            role="user",
            content="Point to M31"
        )

        assert msg.role == "user"
        assert msg.content == "Point to M31"
        assert msg.timestamp is not None

    def test_assistant_message_with_tools(self):
        """Test assistant message with tool calls."""
        tc = ToolCall(id="1", name="goto", arguments={})
        msg = ConversationMessage(
            role="assistant",
            content="",
            tool_calls=[tc]
        )

        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1

    def test_to_dict(self):
        """Test dictionary conversion."""
        msg = ConversationMessage(role="user", content="Hello")
        d = msg.to_dict()

        assert d["role"] == "user"
        assert d["content"] == "Hello"

    def test_to_dict_with_tool_calls(self):
        """Test dictionary conversion with tool calls."""
        tc = ToolCall(id="1", name="test", arguments={"a": 1})
        msg = ConversationMessage(
            role="assistant",
            content="Calling tool",
            tool_calls=[tc]
        )
        d = msg.to_dict()

        assert "tool_calls" in d
        assert d["tool_calls"][0]["name"] == "test"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_basic_response(self):
        """Test basic response."""
        response = LLMResponse(
            content="Hello!",
            model="test-model",
            latency_ms=100.0
        )

        assert response.content == "Hello!"
        assert response.model == "test-model"
        assert response.has_tool_calls is False

    def test_response_with_tool_calls(self):
        """Test response with tool calls."""
        tc = ToolCall(id="1", name="goto", arguments={})
        response = LLMResponse(
            content="",
            tool_calls=[tc]
        )

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test default mock response."""
        client = MockLLMClient()
        response = await client.chat(messages=[])

        assert response.content == "Mock response"
        assert response.model == "mock"

    @pytest.mark.asyncio
    async def test_custom_response(self):
        """Test setting custom response."""
        client = MockLLMClient()
        custom = LLMResponse(content="Custom", model="test")
        client.set_response(custom)

        response = await client.chat(messages=[])

        assert response.content == "Custom"

    @pytest.mark.asyncio
    async def test_call_count(self):
        """Test call counting."""
        client = MockLLMClient()
        await client.chat(messages=[])
        await client.chat(messages=[])

        assert client.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test mock health check."""
        client = MockLLMClient()
        assert await client.health_check() is True


class TestLLMClient:
    """Tests for main LLMClient class."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mock backend."""
        return LLMClient(backend=LLMBackend.MOCK)

    def test_init_with_string_backend(self):
        """Test initializing with string backend."""
        client = LLMClient(backend="mock")
        assert client.backend == LLMBackend.MOCK

    def test_init_with_enum_backend(self):
        """Test initializing with enum backend."""
        client = LLMClient(backend=LLMBackend.MOCK)
        assert client.backend == LLMBackend.MOCK

    def test_default_system_prompt(self, mock_client):
        """Test default system prompt is set."""
        assert mock_client.system_prompt == OBSERVATORY_SYSTEM_PROMPT
        assert "NIGHTWATCH" in mock_client.system_prompt

    def test_custom_system_prompt(self):
        """Test custom system prompt."""
        custom = "You are a test bot."
        client = LLMClient(backend="mock", system_prompt=custom)
        assert client.system_prompt == custom

    def test_token_tracking_initialized(self, mock_client):
        """Test token usage tracker is initialized."""
        assert mock_client.token_usage is not None
        assert mock_client.token_usage.session_total_tokens == 0

    @pytest.mark.asyncio
    async def test_chat_basic(self, mock_client):
        """Test basic chat call."""
        response = await mock_client.chat("Hello")

        assert response is not None
        assert response.content == "Mock response"

    @pytest.mark.asyncio
    async def test_chat_updates_token_usage(self, mock_client):
        """Test chat updates token tracking."""
        await mock_client.chat("Hello")

        usage = mock_client.get_token_usage()
        assert usage["session_total_tokens"] == 15  # Mock returns 10+5

    @pytest.mark.asyncio
    async def test_chat_updates_history(self, mock_client):
        """Test chat updates conversation history."""
        await mock_client.chat("Hello")

        assert len(mock_client._conversation) == 2  # user + assistant
        assert mock_client._conversation[0].role == "user"
        assert mock_client._conversation[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, mock_client):
        """Test chat with tool definitions."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        response = await mock_client.chat("Use the tool", tools=tools)

        assert response is not None

    def test_add_tool_result(self, mock_client):
        """Test adding tool result to history."""
        mock_client.add_tool_result("call_1", "test_tool", "Result data")

        assert len(mock_client._conversation) == 1
        msg = mock_client._conversation[0]
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_1"
        assert msg.name == "test_tool"
        assert msg.content == "Result data"

    def test_clear_history(self, mock_client):
        """Test clearing conversation history."""
        mock_client._conversation.append(
            ConversationMessage(role="user", content="test")
        )
        mock_client.clear_history()

        assert len(mock_client._conversation) == 0

    def test_get_token_usage(self, mock_client):
        """Test getting token usage dict."""
        mock_client.token_usage.add(100, 50)
        usage = mock_client.get_token_usage()

        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert "session_total_tokens" in usage

    def test_reset_session_tokens(self, mock_client):
        """Test resetting session token counters."""
        mock_client.token_usage.add(100, 50)
        mock_client.reset_session_tokens()

        assert mock_client.token_usage.session_total_tokens == 0
        # Current request tokens preserved
        assert mock_client.token_usage.prompt_tokens == 100


class TestLLMClientFallback:
    """Tests for LLM client fallback behavior."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback to secondary backend when primary fails."""
        client = LLMClient(
            backend=LLMBackend.MOCK,
            fallback_backends=[LLMBackend.MOCK]
        )

        # Make primary fail health check
        primary = client._get_client(LLMBackend.MOCK)
        primary.health_check = AsyncMock(return_value=False)

        # Create a second mock that will succeed
        fallback = MockLLMClient()
        fallback.set_response(LLMResponse(content="Fallback response", model="fallback"))
        client._clients[LLMBackend.MOCK] = fallback

        response = await client.chat("Hello")
        assert response.content == "Fallback response"


class TestLLMBackend:
    """Tests for LLMBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        assert LLMBackend.LOCAL.value == "local"
        assert LLMBackend.ANTHROPIC.value == "anthropic"
        assert LLMBackend.OPENAI.value == "openai"
        assert LLMBackend.MOCK.value == "mock"


class TestCreateLLMClient:
    """Tests for factory function."""

    def test_create_mock_client(self):
        """Test creating mock client."""
        client = create_llm_client(backend="mock")
        assert client.backend == LLMBackend.MOCK

    def test_create_with_custom_prompt(self):
        """Test creating client with custom prompt."""
        client = create_llm_client(
            backend="mock",
            system_prompt="Custom prompt"
        )
        assert client.system_prompt == "Custom prompt"


class TestSystemPrompt:
    """Tests for observatory system prompt."""

    def test_prompt_contains_key_info(self):
        """Test system prompt contains necessary context."""
        assert "NIGHTWATCH" in OBSERVATORY_SYSTEM_PROMPT
        assert "telescope" in OBSERVATORY_SYSTEM_PROMPT.lower()
        assert "safety" in OBSERVATORY_SYSTEM_PROMPT.lower()
        assert "tool" in OBSERVATORY_SYSTEM_PROMPT.lower()

    def test_prompt_emphasizes_safety(self):
        """Test safety is emphasized in prompt."""
        assert "Safety First" in OBSERVATORY_SYSTEM_PROMPT
        assert "safety" in OBSERVATORY_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_local_operation(self):
        """Test local operation is mentioned."""
        assert "local" in OBSERVATORY_SYSTEM_PROMPT.lower() or "DGX" in OBSERVATORY_SYSTEM_PROMPT


# ============================================================================
# VOX-002: SafetyStatus injection into LLM context
# ============================================================================


def _make_safety_status(
    *,
    is_safe: bool,
    reasons: list,
    sun_altitude_deg=None,
    wind_speed_mph=None,
):
    """Helper to construct a SafetyStatus with the fields we care about."""
    return SafetyStatus(
        timestamp=datetime.now(),
        action=SafetyAction.SAFE_TO_OBSERVE if is_safe else SafetyAction.PARK_AND_WAIT,
        is_safe=is_safe,
        reasons=reasons,
        alert_level=AlertLevel.INFO if is_safe else AlertLevel.WARNING,
        sun_altitude_deg=sun_altitude_deg,
        wind_speed_mph=wind_speed_mph,
    )


class TestSafetyContextInjection:
    """Tests for VOX-002: SafetyStatus grounding before tool selection."""

    def test_inject_safety_context_returns_none_without_provider(self):
        """No provider set -> returns None (no injection)."""
        client = LLMClient(backend=LLMBackend.MOCK)
        assert client._inject_safety_context() is None

    def test_inject_safety_context_formats_safe_state(self):
        """Provider returns safe SafetyStatus -> formatted OK block."""
        status = _make_safety_status(
            is_safe=True,
            reasons=[],
            sun_altitude_deg=-18.5,
            wind_speed_mph=8.0,
        )
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)
        text = client._inject_safety_context()

        assert text is not None
        assert "SAFETY STATUS: OK" in text
        assert "-18.5" in text  # sun altitude formatted
        assert "8.0 mph" in text

    def test_inject_safety_context_formats_unsafe_state(self):
        """Provider returns unsafe SafetyStatus with 4 reasons -> shows top 3."""
        reasons = [
            "Humidity 92% (above limit)",
            "Inside rain holdoff (12 min remaining)",
            "Wind 28 mph (above park threshold)",
            "Cloud cover 75%",  # 4th, must be excluded
        ]
        status = _make_safety_status(
            is_safe=False,
            reasons=reasons,
            sun_altitude_deg=-6.3,
            wind_speed_mph=28.0,
        )
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)
        text = client._inject_safety_context()

        assert text is not None
        assert "SAFETY STATUS: UNSAFE" in text
        # Top 3 included
        assert "Humidity 92%" in text
        assert "rain holdoff" in text
        assert "Wind 28 mph" in text
        # 4th reason NOT included
        assert "Cloud cover 75%" not in text
        # Trailing instruction
        assert "refuse" in text.lower()
        assert "explain" in text.lower()

    def test_inject_safety_context_handles_provider_exception(self, caplog):
        """Provider raises -> returns None and logs a warning."""
        def boom():
            raise RuntimeError("safety monitor not responding")

        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=boom)
        with caplog.at_level("WARNING", logger="NIGHTWATCH.LLMClient"):
            result = client._inject_safety_context()

        assert result is None
        assert any("safety" in rec.message.lower() for rec in caplog.records)

    def test_inject_safety_context_omits_optional_fields_when_none(self):
        """Optional sun/wind fields absent -> lines omitted gracefully."""
        status = _make_safety_status(is_safe=True, reasons=[])
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)
        text = client._inject_safety_context()

        assert text is not None
        assert "SAFETY STATUS: OK" in text
        assert "Sun altitude" not in text
        assert "Wind:" not in text

    def test_set_safety_provider_wires_post_construction(self):
        """set_safety_provider() works as a post-construction setter."""
        client = LLMClient(backend=LLMBackend.MOCK)
        assert client._inject_safety_context() is None

        status = _make_safety_status(
            is_safe=True, reasons=[], sun_altitude_deg=-20.0, wind_speed_mph=5.0
        )
        client.set_safety_provider(lambda: status)
        text = client._inject_safety_context()
        assert text is not None
        assert "SAFETY STATUS: OK" in text

    @pytest.mark.asyncio
    async def test_chat_includes_safety_context_in_system_message_when_provider_set(self):
        """chat() folds the safety block into the system message before backend call."""
        status = _make_safety_status(
            is_safe=False,
            reasons=["Humidity 92% (above limit)", "Inside rain holdoff (12 min remaining)"],
            sun_altitude_deg=-6.0,
            wind_speed_mph=28.0,
        )
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)

        # Spy on the backend chat() call to capture the messages payload
        backend = client._get_client(LLMBackend.MOCK)
        captured = {}
        original_chat = backend.chat

        async def spy_chat(messages, tools=None, temperature=0.7, max_tokens=1024):
            captured["messages"] = messages
            return await original_chat(messages, tools, temperature, max_tokens)

        backend.chat = spy_chat
        await client.chat("slew to M31")

        msgs = captured["messages"]
        # First message must be the (augmented) system message
        assert msgs[0]["role"] == "system"
        system_content = msgs[0]["content"]
        # Original system prompt preserved
        assert "NIGHTWATCH" in system_content
        # Safety block folded in — discriminating reason text only appears in
        # the live block, not in the static prompt.
        assert "Humidity 92%" in system_content
        assert "rain holdoff" in system_content
        assert "Wind: 28.0 mph" in system_content

    @pytest.mark.asyncio
    async def test_chat_omits_safety_context_when_no_provider(self):
        """No provider -> system message unchanged (backward compat)."""
        client = LLMClient(backend=LLMBackend.MOCK)

        backend = client._get_client(LLMBackend.MOCK)
        captured = {}
        original_chat = backend.chat

        async def spy_chat(messages, tools=None, temperature=0.7, max_tokens=1024):
            captured["messages"] = messages
            return await original_chat(messages, tools, temperature, max_tokens)

        backend.chat = spy_chat
        await client.chat("hi")

        system_content = captured["messages"][0]["content"]
        # System message is exactly the static prompt — no per-turn block appended.
        # (The static prompt itself contains "SAFETY STATUS:" as part of the
        # grounding paragraph that teaches the LLM the pattern, so a substring
        # check on that phrase would not be discriminating; full equality is.)
        assert system_content == OBSERVATORY_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_chat_stream_includes_safety_context_when_provider_set(self):
        """chat_stream() also folds the safety block into the system message."""
        status = _make_safety_status(
            is_safe=False,
            reasons=["Wind 35 mph (gust above limit)"],
            sun_altitude_deg=2.0,
            wind_speed_mph=35.0,
        )
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)

        backend = client._get_client(LLMBackend.MOCK)
        captured = {}
        original_stream = backend.chat_stream

        async def spy_stream(messages, tools=None, temperature=0.7, max_tokens=1024):
            captured["messages"] = messages
            async for chunk in original_stream(messages, tools, temperature, max_tokens):
                yield chunk

        backend.chat_stream = spy_stream
        async for _ in client.chat_stream("open the roof"):
            pass

        system_content = captured["messages"][0]["content"]
        # Discriminating: the specific reason text only appears in the live block.
        assert "Wind 35 mph" in system_content
        assert "gust above limit" in system_content

    @pytest.mark.asyncio
    async def test_chat_succeeds_when_safety_provider_raises(self):
        """If safety_provider fails, chat() still completes (no injection)."""
        def boom():
            raise RuntimeError("safety down")

        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=boom)
        response = await client.chat("hi")
        assert response.content == "Mock response"

    @pytest.mark.asyncio
    async def test_chat_unsafe_grounding_includes_specific_reasons_for_refusal(self):
        """Spec verify line: with unsafe weather, the system message contains the
        live reasons the LLM can quote (e.g. 'humidity 92'), so it can refuse with
        specifics rather than emitting a tool call that the interlock then vetoes."""
        status = _make_safety_status(
            is_safe=False,
            reasons=[
                "Humidity 92% (above 85% limit)",
                "Inside rain holdoff (12 min remaining)",
            ],
            sun_altitude_deg=-5.0,
            wind_speed_mph=12.0,
        )
        client = LLMClient(backend=LLMBackend.MOCK, safety_provider=lambda: status)

        backend = client._get_client(LLMBackend.MOCK)
        captured = {}
        original_chat = backend.chat

        async def spy_chat(messages, tools=None, temperature=0.7, max_tokens=1024):
            captured["messages"] = messages
            return await original_chat(messages, tools, temperature, max_tokens)

        backend.chat = spy_chat
        await client.chat("slew to M31")

        system_content = captured["messages"][0]["content"]
        # Reasons appear verbatim so the LLM can quote them back
        assert "Humidity 92%" in system_content
        assert "rain holdoff" in system_content
        # Refusal instruction is present in the injected block. The static
        # prompt and the injected block use the same vocabulary
        # ("refuse mount, camera, and enclosure tool calls") so the assertion
        # below would also match the static text — that's fine; it confirms
        # the instruction is reaching the model on this turn.
        assert "refuse mount, camera, and enclosure" in system_content.lower()
        # The OBSERVATORY_SYSTEM_PROMPT itself teaches the LLM what to do
        # when it sees SAFETY STATUS: UNSAFE
        assert "SAFETY STATUS" in OBSERVATORY_SYSTEM_PROMPT


class TestObservatorySystemPromptGrounding:
    """Tests that OBSERVATORY_SYSTEM_PROMPT teaches the model about the
    injected safety block (VOX-002)."""

    def test_prompt_mentions_safety_status_pattern(self):
        """Prompt explicitly names the SAFETY STATUS: pattern."""
        assert "SAFETY STATUS" in OBSERVATORY_SYSTEM_PROMPT

    def test_prompt_teaches_refusal_on_unsafe(self):
        """Prompt instructs the model to refuse mount/camera tools on UNSAFE."""
        text = OBSERVATORY_SYSTEM_PROMPT.lower()
        assert "unsafe" in text
        assert "refuse" in text
