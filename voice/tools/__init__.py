"""
NIGHTWATCH Voice Tools

LLM function calling tools for telescope control and meteor tracking.
"""

from .telescope_tools import (
    Tool,
    ToolParameter,
    ToolCategory,
    ToolRegistry,
    TELESCOPE_TOOLS,
    TELESCOPE_SYSTEM_PROMPT,
    create_default_handlers,
)

from .meteor_tools import (
    METEOR_TOOLS,
    MeteorToolHandler,
    get_all_meteor_tools,
    get_meteor_tool_schemas,
)

__all__ = [
    # Core tool infrastructure
    "Tool",
    "ToolParameter",
    "ToolCategory",
    "ToolRegistry",
    # Telescope tools
    "TELESCOPE_TOOLS",
    "TELESCOPE_SYSTEM_PROMPT",
    "create_default_handlers",
    # Meteor tools
    "METEOR_TOOLS",
    "MeteorToolHandler",
    "get_all_meteor_tools",
    "get_meteor_tool_schemas",
]
