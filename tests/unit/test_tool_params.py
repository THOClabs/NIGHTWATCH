"""
Unit tests for ARCH-001 Pydantic parameter models.

Validates that every tool exposed by ``ToolExecutor`` has a corresponding
Pydantic model registered in ``TOOL_PARAM_MODELS`` and that each model
enforces its declared schema (types, required fields, ``extra='forbid'``).

These tests live separately from ``test_tool_executor.py`` so they can be
read as the spec for ``nightwatch.tool_params``.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import ValidationError

from nightwatch.tool_params import (
    TOOL_PARAM_MODELS,
    GetPlanetPositionParams,
    GotoCoordinatesParams,
    GotoObjectParams,
    LookupObjectParams,
    NoParams,
    StartSessionParams,
    WhatIsParams,
)

# =============================================================================
# Registry coverage
# =============================================================================


class TestRegistryCoverage:
    """Every registered tool name must map to a Pydantic BaseModel subclass."""

    REGISTERED_TOOLS: ClassVar[set[str]] = {
        # Mount control (1 param-taking, 4 no-param)
        "goto_object",
        "goto_coordinates",
        "park_telescope",
        "unpark_telescope",
        "stop_mount",
        "get_mount_status",
        # Catalog
        "lookup_object",
        "what_is",
        # Ephemeris
        "get_planet_position",
        "get_sun_status",
        "get_twilight_times",
        # Weather
        "get_weather",
        "is_weather_safe",
        # Safety
        "get_safety_status",
        "check_can_observe",
        # Session
        "start_session",
        "end_session",
        "get_session_status",
    }

    def test_registry_covers_all_18_tools(self):
        """TOOL_PARAM_MODELS includes every tool registered by ToolExecutor."""
        missing = self.REGISTERED_TOOLS - set(TOOL_PARAM_MODELS.keys())
        assert not missing, f"Missing param models for tools: {missing}"

    def test_registry_has_no_extra_entries(self):
        """No phantom entries in TOOL_PARAM_MODELS."""
        extras = set(TOOL_PARAM_MODELS.keys()) - self.REGISTERED_TOOLS
        assert not extras, f"Unexpected param models for tools: {extras}"

    def test_all_models_forbid_extra_fields(self):
        """extra='forbid' on every model — silently-dropped junk is a bug."""
        for name, model_cls in TOOL_PARAM_MODELS.items():
            cfg = getattr(model_cls, "model_config", {})
            extra = cfg.get("extra")
            assert extra == "forbid", (
                f"Tool {name!r} model {model_cls.__name__} must set "
                f"model_config=ConfigDict(extra='forbid'); got {extra!r}"
            )


# =============================================================================
# GotoObjectParams
# =============================================================================


class TestGotoObjectParams:
    def test_happy_path(self):
        params = GotoObjectParams(object_name="M31")
        assert params.object_name == "M31"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            GotoObjectParams(object_name=42)
        msg = str(exc_info.value).lower()
        assert "object_name" in msg
        assert "str" in msg or "string" in msg

    def test_missing_required_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            GotoObjectParams()
        assert "object_name" in str(exc_info.value).lower()

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            GotoObjectParams(object_name="M31", extra="x")
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# GotoCoordinatesParams (Union[float, str] for ra/dec)
# =============================================================================


class TestGotoCoordinatesParams:
    def test_happy_path_floats(self):
        params = GotoCoordinatesParams(ra=10.5, dec=41.2)
        assert params.ra == 10.5
        assert params.dec == 41.2

    def test_happy_path_strings(self):
        # The downstream handler supports HH:MM:SS / sDD:MM:SS — preserve that.
        params = GotoCoordinatesParams(ra="10:30:00", dec="+41:12:00")
        assert params.ra == "10:30:00"
        assert params.dec == "+41:12:00"

    def test_missing_ra_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            GotoCoordinatesParams(dec=41.2)
        assert "ra" in str(exc_info.value).lower()

    def test_missing_dec_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            GotoCoordinatesParams(ra=10.5)
        assert "dec" in str(exc_info.value).lower()

    def test_invalid_type_rejected(self):
        # bool / list / dict are not float-or-str
        with pytest.raises(ValidationError):
            GotoCoordinatesParams(ra=[1, 2, 3], dec=41.2)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            GotoCoordinatesParams(ra=10.5, dec=41.2, frame="J2000")

    def test_bool_rejected_for_ra(self):
        """Pydantic coerces bool→float by default; reject for safety."""
        with pytest.raises(ValidationError, match="bool"):
            GotoCoordinatesParams(ra=True, dec=0.0)

    def test_bool_rejected_for_dec(self):
        with pytest.raises(ValidationError, match="bool"):
            GotoCoordinatesParams(ra=0.0, dec=False)


# =============================================================================
# LookupObjectParams / WhatIsParams (both use object_name: str)
# =============================================================================


class TestLookupObjectParams:
    def test_happy_path(self):
        assert LookupObjectParams(object_name="M42").object_name == "M42"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            LookupObjectParams(object_name=123)

    def test_missing_required_rejected(self):
        with pytest.raises(ValidationError):
            LookupObjectParams()

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            LookupObjectParams(object_name="M42", catalog="messier")


class TestWhatIsParams:
    def test_happy_path(self):
        assert WhatIsParams(object_name="Andromeda").object_name == "Andromeda"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            WhatIsParams(object_name=None)

    def test_missing_required_rejected(self):
        with pytest.raises(ValidationError):
            WhatIsParams()

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            WhatIsParams(object_name="Andromeda", detail="long")


# =============================================================================
# GetPlanetPositionParams
# =============================================================================


class TestGetPlanetPositionParams:
    def test_happy_path(self):
        assert GetPlanetPositionParams(planet="mars").planet == "mars"

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            GetPlanetPositionParams(planet=7)

    def test_missing_required_rejected(self):
        with pytest.raises(ValidationError):
            GetPlanetPositionParams()

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            GetPlanetPositionParams(planet="mars", time="now")


# =============================================================================
# StartSessionParams (session_id is Optional — orchestrator generates one if None)
# =============================================================================


class TestStartSessionParams:
    def test_happy_path_with_id(self):
        assert StartSessionParams(session_id="run-001").session_id == "run-001"

    def test_session_id_optional(self):
        # Orchestrator generates a session_id if caller doesn't supply one.
        params = StartSessionParams()
        assert params.session_id is None

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            StartSessionParams(session_id=42)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            StartSessionParams(session_id="run-001", notes="x")


# =============================================================================
# NoParams (12 zero-arg tools)
# =============================================================================


class TestNoParams:
    def test_empty_dict_accepted(self):
        params = NoParams()
        assert params is not None

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            NoParams(anything="x")


# =============================================================================
# Per-model registry mapping
# =============================================================================


class TestRegistryMapping:
    """Spot-check that the registry maps each name to the right model."""

    @pytest.mark.parametrize(
        "name,model_cls",
        [
            ("goto_object", GotoObjectParams),
            ("goto_coordinates", GotoCoordinatesParams),
            ("lookup_object", LookupObjectParams),
            ("what_is", WhatIsParams),
            ("get_planet_position", GetPlanetPositionParams),
            ("start_session", StartSessionParams),
            ("park_telescope", NoParams),
            ("get_mount_status", NoParams),
            ("get_weather", NoParams),
            ("get_safety_status", NoParams),
            ("end_session", NoParams),
            ("get_session_status", NoParams),
        ],
    )
    def test_mapping(self, name, model_cls):
        assert TOOL_PARAM_MODELS[name] is model_cls
