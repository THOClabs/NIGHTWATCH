"""
NIGHTWATCH Voice LLM Tools
Meteor Tracking Function Definitions

Voice commands for meteor and fireball tracking.
Integrates with the meteor_tracking service.
"""

from dataclasses import dataclass
from typing import List, Optional

# Import from telescope_tools to use same patterns
from .telescope_tools import Tool, ToolParameter, ToolCategory


# Add METEOR category to ToolCategory (extend existing enum concept)
# Note: In production, add to the ToolCategory enum in telescope_tools.py
METEOR_CATEGORY = "meteor"


METEOR_TOOLS: List[Tool] = [
    # -------------------------------------------------------------------------
    # METEOR WATCH TOOLS
    # -------------------------------------------------------------------------
    Tool(
        name="watch_for_meteors",
        description="Set up a meteor watch window. Accepts natural language like "
                    "'watch for the Perseids next week' or 'keep an eye on the sky tonight'. "
                    "NIGHTWATCH will monitor fireball databases and alert when events are detected.",
        category=ToolCategory.ALERTS,  # Use ALERTS category for now
        parameters=[
            ToolParameter(
                name="request",
                type="string",
                description="Natural language watch request (e.g., 'Perseids next week', "
                           "'tonight from Astoria', 'Quadrantids January 3-4')"
            )
        ]
    ),

    Tool(
        name="get_meteor_status",
        description="Get the current status of meteor tracking. Shows active watch windows, "
                    "recent detections, and next major meteor shower.",
        category=ToolCategory.ALERTS,
        parameters=[]
    ),

    Tool(
        name="get_meteor_shower_info",
        description="Get information about meteor showers. Without a name, shows upcoming showers. "
                    "With a name, shows detailed information about that specific shower.",
        category=ToolCategory.EPHEMERIS,
        parameters=[
            ToolParameter(
                name="shower_name",
                type="string",
                description="Name of meteor shower (e.g., 'Perseids', 'Geminids'). "
                           "Optional - leave blank for upcoming showers.",
                required=False
            )
        ]
    ),

    Tool(
        name="check_for_fireballs",
        description="Manually trigger a check for new fireballs. Queries NASA CNEOS and "
                    "American Meteor Society databases for recent events visible from "
                    "the current watch location.",
        category=ToolCategory.ALERTS,
        parameters=[]
    ),

    Tool(
        name="get_active_watch_windows",
        description="List all currently active meteor watch windows with their locations, "
                    "time ranges, and associated meteor showers.",
        category=ToolCategory.ALERTS,
        parameters=[]
    ),
]


def get_all_meteor_tools() -> List[Tool]:
    """Get all meteor tracking tools for registration with voice pipeline."""
    return METEOR_TOOLS


def get_meteor_tool_schemas() -> List[dict]:
    """Get OpenAI-format schemas for all meteor tools."""
    return [tool.to_openai_format() for tool in METEOR_TOOLS]


# =============================================================================
# TOOL HANDLER IMPLEMENTATIONS
# =============================================================================

class MeteorToolHandler:
    """
    Handler for meteor tracking voice commands.

    Connects voice tools to the MeteorTrackingService.
    """

    def __init__(self, meteor_service):
        """
        Initialize handler with meteor service.

        Args:
            meteor_service: Instance of MeteorTrackingService
        """
        self.service = meteor_service

    async def handle_tool_call(self, tool_name: str, arguments: dict) -> str:
        """
        Handle a tool call from the voice pipeline.

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments from LLM

        Returns:
            Response string for TTS
        """
        if tool_name == "watch_for_meteors":
            return await self._watch_for_meteors(arguments)
        elif tool_name == "get_meteor_status":
            return await self._get_meteor_status()
        elif tool_name == "get_meteor_shower_info":
            return await self._get_meteor_shower_info(arguments)
        elif tool_name == "check_for_fireballs":
            return await self._check_for_fireballs()
        elif tool_name == "get_active_watch_windows":
            return await self._get_active_watch_windows()
        else:
            return f"Unknown meteor tool: {tool_name}"

    async def _watch_for_meteors(self, arguments: dict) -> str:
        """Handle watch_for_meteors tool."""
        request = arguments.get("request", "")
        if not request:
            return "Please specify what to watch for. For example, 'watch for the Perseids next week'."

        result = await self.service.add_watch(request)

        # Convert prayer to spoken response
        # Parse out key info for voice
        lines = result.split('\n')
        window_line = lines[0] if lines else ""

        # Find shower and time info
        shower_info = ""
        time_info = ""
        for line in lines:
            if "shower-name:" in line:
                shower_info = line.split(":")[1].strip()
            if "watch-window:" in line:
                time_info = line.split(":")[1].strip()

        if shower_info:
            return f"Watch window created for {shower_info}. I'll monitor for fireballs and alert you when events are detected."
        elif time_info:
            return f"Watch window created for {time_info}. Meteor tracking is now active."
        else:
            return "Watch window created. Meteor tracking is now active."

    async def _get_meteor_status(self) -> str:
        """Handle get_meteor_status tool."""
        status = await self.service.get_status()

        # Parse status for voice
        active = 0
        known = 0
        next_shower = None

        for line in status.split('\n'):
            if "watch-windows-active:" in line:
                val = line.split(":")[1].strip()
                if val != "ne":
                    active = int(val)
            if "fireballs-known:" in line:
                known = int(line.split(":")[1].strip())
            if "next-major-shower:" in line:
                next_shower = line.split(":")[1].strip()

        parts = []
        if active > 0:
            parts.append(f"{active} active watch window{'s' if active != 1 else ''}")
        else:
            parts.append("No active watch windows")

        parts.append(f"{known} fireballs tracked")

        if next_shower:
            parts.append(f"Next major shower: {next_shower}")

        return ". ".join(parts) + "."

    async def _get_meteor_shower_info(self, arguments: dict) -> str:
        """Handle get_meteor_shower_info tool."""
        shower_name = arguments.get("shower_name")
        info = await self.service.get_shower_info(shower_name)

        # Format for voice
        if "not found" in info.lower():
            return info

        # Parse first few lines for voice
        lines = info.split('\n')
        if shower_name and len(lines) > 2:
            # Specific shower
            name = lines[0].replace("Meteor Shower: ", "")
            peak = lines[1].replace("Peak: ", "")
            zhr = lines[2].replace("ZHR: ", "")
            return f"{name} peaks on {peak} with up to {zhr}."
        else:
            # Upcoming showers - summarize first 2
            response_parts = []
            for line in lines:
                if line.strip().startswith("ZHR:"):
                    continue
                if ":" in line and not line.startswith(" "):
                    response_parts.append(line.strip())
                if len(response_parts) >= 3:
                    break
            return " ".join(response_parts[:3])

    async def _check_for_fireballs(self) -> str:
        """Handle check_for_fireballs tool."""
        result = await self.service.check_now()
        return result

    async def _get_active_watch_windows(self) -> str:
        """Handle get_active_watch_windows tool."""
        windows = self.service.get_active_windows()

        if not windows:
            return "No active watch windows. Say 'watch for meteors tonight' to create one."

        if len(windows) == 1:
            w = windows[0]
            response = f"One active watch window: {w.location_name}"
            if w.shower_name:
                response += f" for {w.shower_name}"
            response += f" until {w.end_time.strftime('%I:%M %p')}."
            return response

        return f"{len(windows)} active watch windows covering {windows[0].location_name} and other locations."
