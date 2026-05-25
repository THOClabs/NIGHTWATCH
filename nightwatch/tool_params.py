"""
NIGHTWATCH Tool Parameter Models (ARCH-001).

Pydantic v2 models that validate the ``parameters`` dict an LLM passes into
``ToolExecutor.execute()``. Risk #1 from the Phase 1 audit: the previous
contract was ``Dict[str, Any]`` with ``params.get(...)`` everywhere, which
silently dropped wrong types and missing fields. Garbage from a sloppy LLM
turn could reach a service handler and hang the voice pipeline.

This module:

  * Defines one ``BaseModel`` per tool that takes parameters
    (``GotoObjectParams``, ``GotoCoordinatesParams``, ``LookupObjectParams``,
    ``WhatIsParams``, ``GetPlanetPositionParams``, ``StartSessionParams``).
  * Defines ``NoParams`` for the 12 tools that take no parameters; this
    keeps the dispatch code uniform and rejects stray ``extra`` fields
    rather than silently ignoring them.
  * Exposes ``TOOL_PARAM_MODELS``: a registry mapping every tool name
    registered by ``ToolExecutor._register_default_handlers`` to its model.

Every model sets ``extra='forbid'`` so unexpected fields produce a
``ValidationError`` rather than slipping through.

VOX-003 will reuse ``TOOL_PARAM_MODELS`` to validate LLM tool-call
arguments before they reach ``ToolExecutor.execute`` at all.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Param-taking tools
# =============================================================================


class GotoObjectParams(BaseModel):
    """Parameters for ``goto_object`` — slew to a named catalog object."""

    model_config = ConfigDict(extra="forbid")

    object_name: str = Field(
        ...,
        description="Catalog name of the object (e.g. 'M31', 'Andromeda', 'NGC 1234').",
    )


class GotoCoordinatesParams(BaseModel):
    """Parameters for ``goto_coordinates`` — slew to explicit RA/Dec.

    ``ra`` and ``dec`` accept either a float (decimal hours / decimal
    degrees) or a string (``HH:MM:SS`` / ``sDD:MM:SS``). The handler
    coerces strings via ``_parse_ra`` / ``_parse_dec``.
    """

    model_config = ConfigDict(extra="forbid")

    ra: float | str = Field(
        ...,
        description=(
            "Right ascension — either decimal hours (float) or 'HH:MM:SS' string."
        ),
    )
    dec: float | str = Field(
        ...,
        description=(
            "Declination — either decimal degrees (float) or 'sDD:MM:SS' string."
        ),
    )


class LookupObjectParams(BaseModel):
    """Parameters for ``lookup_object`` — fetch catalog entry by name."""

    model_config = ConfigDict(extra="forbid")

    object_name: str = Field(
        ...,
        description="Catalog name of the object to look up.",
    )


class WhatIsParams(BaseModel):
    """Parameters for ``what_is`` — conversational object description."""

    model_config = ConfigDict(extra="forbid")

    object_name: str = Field(
        ...,
        description="Catalog name of the object to describe.",
    )


class GetPlanetPositionParams(BaseModel):
    """Parameters for ``get_planet_position`` — current planet RA/Dec."""

    model_config = ConfigDict(extra="forbid")

    planet: str = Field(
        ...,
        description="Planet name (e.g. 'mars', 'jupiter', 'venus'). Case-insensitive.",
    )


class StartSessionParams(BaseModel):
    """Parameters for ``start_session`` — begin an observing session.

    ``session_id`` is optional; when omitted the orchestrator generates one
    (typically a UTC timestamp). This matches the existing handler contract.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(
        default=None,
        description=(
            "Caller-supplied session identifier. If omitted the orchestrator "
            "generates one."
        ),
    )


# =============================================================================
# Zero-arg tools
# =============================================================================


class NoParams(BaseModel):
    """Empty parameter set for zero-arg tools.

    Used for: ``park_telescope``, ``unpark_telescope``, ``stop_mount``,
    ``get_mount_status``, ``get_sun_status``, ``get_twilight_times``,
    ``get_weather``, ``is_weather_safe``, ``get_safety_status``,
    ``check_can_observe``, ``end_session``, ``get_session_status``.

    Validates that the caller passes ``{}`` (or any subset of allowed
    fields — there are none) and rejects stray ``extra`` keys.
    """

    model_config = ConfigDict(extra="forbid")


# =============================================================================
# Registry
# =============================================================================


# Maps every tool name registered by ``ToolExecutor._register_default_handlers``
# to its parameter model. ``ToolExecutor.execute`` looks the model up here and
# validates the inbound ``parameters`` dict before dispatching to the handler.
TOOL_PARAM_MODELS: dict[str, type[BaseModel]] = {
    # Mount control
    "goto_object": GotoObjectParams,
    "goto_coordinates": GotoCoordinatesParams,
    "park_telescope": NoParams,
    "unpark_telescope": NoParams,
    "stop_mount": NoParams,
    "get_mount_status": NoParams,
    # Catalog
    "lookup_object": LookupObjectParams,
    "what_is": WhatIsParams,
    # Ephemeris
    "get_planet_position": GetPlanetPositionParams,
    "get_sun_status": NoParams,
    "get_twilight_times": NoParams,
    # Weather
    "get_weather": NoParams,
    "is_weather_safe": NoParams,
    # Safety
    "get_safety_status": NoParams,
    "check_can_observe": NoParams,
    # Session
    "start_session": StartSessionParams,
    "end_session": NoParams,
    "get_session_status": NoParams,
}


__all__ = [
    "TOOL_PARAM_MODELS",
    "GetPlanetPositionParams",
    "GotoCoordinatesParams",
    "GotoObjectParams",
    "LookupObjectParams",
    "NoParams",
    "StartSessionParams",
    "WhatIsParams",
]
