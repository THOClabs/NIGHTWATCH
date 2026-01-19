"""
NIGHTWATCH Response Formatter
Formats tool results into natural language responses for TTS.

Converts structured data from tool executions into human-friendly
speech responses that sound natural when spoken aloud.

Usage:
    from nightwatch.response_formatter import ResponseFormatter

    formatter = ResponseFormatter()

    # Format a tool result
    result = ToolResult(...)
    speech = formatter.format(result)

    # Format specific data types
    ra_text = formatter.format_ra(10.685)  # "10 hours 41 minutes"
    weather_text = formatter.format_weather(conditions)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger("NIGHTWATCH.ResponseFormatter")


__all__ = [
    "ResponseFormatter",
    "format_ra",
    "format_dec",
    "format_alt_az",
    "format_temperature",
    "format_wind",
    "format_time",
]


# =============================================================================
# Standalone Formatting Functions
# =============================================================================


def format_ra(ra_hours: float, precision: str = "minutes") -> str:
    """
    Format Right Ascension as spoken text.

    Args:
        ra_hours: RA in decimal hours (0-24)
        precision: "hours", "minutes", or "seconds"

    Returns:
        Spoken text like "10 hours 41 minutes"
    """
    hours = int(ra_hours)
    minutes = int((ra_hours - hours) * 60)
    seconds = int(((ra_hours - hours) * 60 - minutes) * 60)

    if precision == "hours":
        return f"{hours} hours"
    elif precision == "minutes":
        if minutes == 0:
            return f"{hours} hours"
        return f"{hours} hours {minutes} minutes"
    else:  # seconds
        if seconds == 0:
            if minutes == 0:
                return f"{hours} hours"
            return f"{hours} hours {minutes} minutes"
        return f"{hours} hours {minutes} minutes {seconds} seconds"


def format_dec(dec_degrees: float, precision: str = "arcmin") -> str:
    """
    Format Declination as spoken text.

    Args:
        dec_degrees: Dec in decimal degrees (-90 to +90)
        precision: "degrees", "arcmin", or "arcsec"

    Returns:
        Spoken text like "plus 41 degrees 16 arcminutes"
    """
    sign = "plus" if dec_degrees >= 0 else "minus"
    dec_abs = abs(dec_degrees)
    degrees = int(dec_abs)
    arcmin = int((dec_abs - degrees) * 60)
    arcsec = int(((dec_abs - degrees) * 60 - arcmin) * 60)

    if precision == "degrees":
        return f"{sign} {degrees} degrees"
    elif precision == "arcmin":
        if arcmin == 0:
            return f"{sign} {degrees} degrees"
        return f"{sign} {degrees} degrees {arcmin} arcminutes"
    else:  # arcsec
        if arcsec == 0:
            if arcmin == 0:
                return f"{sign} {degrees} degrees"
            return f"{sign} {degrees} degrees {arcmin} arcminutes"
        return f"{sign} {degrees} degrees {arcmin} arcminutes {arcsec} arcseconds"


def format_alt_az(altitude: float, azimuth: float) -> str:
    """
    Format Alt/Az coordinates as spoken text.

    Args:
        altitude: Altitude in degrees
        azimuth: Azimuth in degrees

    Returns:
        Spoken text like "altitude 45 degrees, azimuth 180 degrees"
    """
    # Convert azimuth to cardinal direction
    directions = ["north", "northeast", "east", "southeast",
                  "south", "southwest", "west", "northwest"]
    idx = int((azimuth + 22.5) / 45) % 8
    direction = directions[idx]

    if altitude < 0:
        return f"below the horizon, {direction}"
    elif altitude < 10:
        return f"low in the {direction}, altitude {altitude:.0f} degrees"
    elif altitude > 80:
        return f"nearly overhead, altitude {altitude:.0f} degrees"
    else:
        return f"altitude {altitude:.0f} degrees, toward the {direction}"


def format_temperature(temp_c: float, unit: str = "celsius") -> str:
    """
    Format temperature as spoken text.

    Args:
        temp_c: Temperature in Celsius
        unit: "celsius" or "fahrenheit"

    Returns:
        Spoken text like "15 degrees celsius"
    """
    if unit == "fahrenheit":
        temp_f = temp_c * 9/5 + 32
        return f"{temp_f:.0f} degrees fahrenheit"
    return f"{temp_c:.0f} degrees celsius"


def format_wind(speed_kph: float, direction_deg: Optional[float] = None) -> str:
    """
    Format wind conditions as spoken text.

    Args:
        speed_kph: Wind speed in km/h
        direction_deg: Wind direction in degrees (0=N, 90=E, etc.)

    Returns:
        Spoken text like "15 kilometers per hour from the west"
    """
    if speed_kph < 1:
        return "calm"
    elif speed_kph < 5:
        return "light breeze"

    speed_text = f"{speed_kph:.0f} kilometers per hour"

    if direction_deg is not None:
        directions = ["north", "northeast", "east", "southeast",
                      "south", "southwest", "west", "northwest"]
        idx = int((direction_deg + 22.5) / 45) % 8
        return f"{speed_text} from the {directions[idx]}"

    return speed_text


def format_time(dt: datetime, include_date: bool = False) -> str:
    """
    Format datetime as spoken text.

    Args:
        dt: Datetime to format
        include_date: Include date in output

    Returns:
        Spoken text like "8:30 PM" or "January 15th at 8:30 PM"
    """
    hour = dt.hour
    minute = dt.minute
    am_pm = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12
    if hour_12 == 0:
        hour_12 = 12

    if minute == 0:
        time_str = f"{hour_12} {am_pm}"
    else:
        time_str = f"{hour_12}:{minute:02d} {am_pm}"

    if include_date:
        day = dt.day
        suffix = "th"
        if day in [1, 21, 31]:
            suffix = "st"
        elif day in [2, 22]:
            suffix = "nd"
        elif day in [3, 23]:
            suffix = "rd"
        date_str = dt.strftime(f"%B {day}{suffix}")
        return f"{date_str} at {time_str}"

    return time_str


def format_duration(seconds: float) -> str:
    """
    Format duration as spoken text.

    Args:
        seconds: Duration in seconds

    Returns:
        Spoken text like "2 minutes 30 seconds"
    """
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        if secs == 0:
            return f"{minutes} minutes"
        return f"{minutes} minutes {secs} seconds"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        if minutes == 0:
            return f"{hours} hours"
        return f"{hours} hours {minutes} minutes"


# =============================================================================
# Response Templates
# =============================================================================


RESPONSE_TEMPLATES = {
    # Mount responses
    "slew_complete": "Now pointing at {object}.",
    "slew_complete_coords": "Slew complete. Now at RA {ra}, Dec {dec}.",
    "mount_parked": "The telescope is now parked.",
    "mount_unparked": "The telescope is unparked and ready.",
    "mount_stopped": "Mount motion stopped.",

    # Catalog responses
    "object_found": "{name} is a {type} in the constellation {constellation}.",
    "object_not_found": "I couldn't find an object called {name}.",

    # Weather responses
    "weather_safe": "Weather conditions are safe for observing.",
    "weather_unsafe": "Weather is currently unsafe. {reason}",
    "weather_summary": "Temperature is {temp}, humidity {humidity} percent, wind {wind}.",

    # Safety responses
    "all_safe": "All systems are safe. Ready to observe.",
    "not_safe": "Warning: {reasons}",

    # Session responses
    "session_started": "Observing session started.",
    "session_ended": "Session complete. Captured {count} images totaling {exposure} of exposure.",

    # Twilight responses
    "twilight_evening": "Astronomical twilight ends at {time}.",
    "twilight_morning": "Astronomical twilight begins at {time}.",

    # Error responses
    "service_unavailable": "The {service} is not currently available.",
    "command_failed": "Sorry, I couldn't {action}. {reason}",
}


# =============================================================================
# Response Formatter Class
# =============================================================================


class ResponseFormatter:
    """
    Formats tool results into natural language for TTS.

    Handles conversion of structured data into spoken responses,
    using templates and formatting functions for consistency.
    """

    def __init__(self, templates: Optional[Dict[str, str]] = None):
        """
        Initialize formatter.

        Args:
            templates: Optional custom templates to merge with defaults
        """
        self.templates = RESPONSE_TEMPLATES.copy()
        if templates:
            self.templates.update(templates)

    def format(self, result) -> str:
        """
        Format a ToolResult into spoken text.

        Args:
            result: ToolResult from tool_executor

        Returns:
            Natural language response string
        """
        # If result already has a good message, use it
        if result.message and len(result.message) > 10:
            return result.message

        # Try to build a better response from data
        tool_name = result.tool_name
        data = result.data or {}

        # Route to specific formatters based on tool
        if tool_name == "goto_object" and result.success:
            return self._format_slew(data)
        elif tool_name == "get_weather" and result.success:
            return self._format_weather(data)
        elif tool_name == "get_twilight_times" and result.success:
            return self._format_twilight(data)
        elif tool_name == "get_safety_status":
            return self._format_safety(data)

        # Fall back to message
        return result.message or "Done."

    def _format_slew(self, data: Dict[str, Any]) -> str:
        """Format slew completion response."""
        obj = data.get("object")
        if obj:
            return self.templates["slew_complete"].format(object=obj)

        ra = data.get("ra")
        dec = data.get("dec")
        if ra is not None and dec is not None:
            ra_text = format_ra(ra, "minutes")
            dec_text = format_dec(dec, "arcmin")
            return f"Now pointing at {ra_text}, {dec_text}."

        return "Slew complete."

    def _format_weather(self, data: Dict[str, Any]) -> str:
        """Format weather conditions response."""
        parts = []

        temp = data.get("temperature") or data.get("temp_c")
        if temp is not None:
            parts.append(f"Temperature is {format_temperature(temp)}")

        humidity = data.get("humidity")
        if humidity is not None:
            parts.append(f"humidity {humidity:.0f} percent")

        wind = data.get("wind_speed") or data.get("wind_kph")
        if wind is not None:
            wind_dir = data.get("wind_direction")
            parts.append(f"wind {format_wind(wind, wind_dir)}")

        cloud = data.get("cloud_cover")
        if cloud is not None:
            if cloud < 20:
                parts.append("skies are clear")
            elif cloud < 50:
                parts.append("partly cloudy")
            elif cloud < 80:
                parts.append("mostly cloudy")
            else:
                parts.append("overcast")

        if not parts:
            return "Weather data retrieved."

        return ". ".join(parts) + "."

    def _format_twilight(self, data: Dict[str, Any]) -> str:
        """Format twilight times response."""
        parts = []

        sunset = data.get("sunset")
        if sunset:
            if isinstance(sunset, str):
                parts.append(f"Sunset is at {sunset}")
            elif isinstance(sunset, datetime):
                parts.append(f"Sunset is at {format_time(sunset)}")

        astro_end = data.get("astronomical_twilight_end") or data.get("astro_end")
        if astro_end:
            if isinstance(astro_end, str):
                parts.append(f"astronomical darkness begins at {astro_end}")
            elif isinstance(astro_end, datetime):
                parts.append(f"astronomical darkness begins at {format_time(astro_end)}")

        astro_start = data.get("astronomical_twilight_start") or data.get("astro_start")
        if astro_start:
            if isinstance(astro_start, str):
                parts.append(f"morning twilight at {astro_start}")
            elif isinstance(astro_start, datetime):
                parts.append(f"morning twilight at {format_time(astro_start)}")

        sunrise = data.get("sunrise")
        if sunrise:
            if isinstance(sunrise, str):
                parts.append(f"sunrise at {sunrise}")
            elif isinstance(sunrise, datetime):
                parts.append(f"sunrise at {format_time(sunrise)}")

        if not parts:
            return "Twilight times retrieved."

        return ", ".join(parts) + "."

    def _format_safety(self, data: Dict[str, Any]) -> str:
        """Format safety status response."""
        is_safe = data.get("is_safe", True)
        reasons = data.get("unsafe_reasons", [])

        if is_safe:
            return self.templates["all_safe"]

        if reasons:
            reason_text = ", ".join(reasons)
            return self.templates["not_safe"].format(reasons=reason_text)

        return "Safety status: unsafe"

    # =========================================================================
    # Object Description Formatting
    # =========================================================================

    def format_object_info(self, obj_data: Dict[str, Any]) -> str:
        """
        Format celestial object information as spoken text.

        Args:
            obj_data: Object data from catalog

        Returns:
            Natural description of the object
        """
        name = obj_data.get("name") or obj_data.get("catalog_id", "This object")
        obj_type = obj_data.get("type") or obj_data.get("object_type", "")
        constellation = obj_data.get("constellation", "")
        magnitude = obj_data.get("magnitude")

        parts = [name]

        if obj_type:
            parts.append(f"is a {obj_type.lower()}")

        if constellation:
            parts.append(f"in the constellation {constellation}")

        if magnitude is not None:
            if magnitude < 1:
                parts.append("and is one of the brightest objects in the sky")
            elif magnitude < 4:
                parts.append("and is easily visible to the naked eye")
            elif magnitude < 6:
                parts.append("and is visible to the naked eye under dark skies")
            elif magnitude < 10:
                parts.append("and requires binoculars or a small telescope")
            else:
                parts.append("and requires a telescope to observe")

        return " ".join(parts) + "."

    # =========================================================================
    # Coordinate Formatting
    # =========================================================================

    def format_coordinates(
        self,
        ra: Optional[float] = None,
        dec: Optional[float] = None,
        alt: Optional[float] = None,
        az: Optional[float] = None
    ) -> str:
        """
        Format coordinates as spoken text.

        Args:
            ra: Right Ascension in hours
            dec: Declination in degrees
            alt: Altitude in degrees
            az: Azimuth in degrees

        Returns:
            Spoken coordinate description
        """
        parts = []

        if ra is not None and dec is not None:
            parts.append(f"Right Ascension {format_ra(ra)}")
            parts.append(f"Declination {format_dec(dec)}")

        if alt is not None and az is not None:
            parts.append(format_alt_az(alt, az))

        if not parts:
            return "Coordinates not available."

        return ", ".join(parts) + "."

    # =========================================================================
    # Error Message Formatting
    # =========================================================================

    def format_error(self, error: str, context: Optional[str] = None) -> str:
        """
        Format an error message for speech.

        Args:
            error: Error message
            context: Optional context (what was being attempted)

        Returns:
            User-friendly error message
        """
        # Clean up common error patterns
        error = error.replace("_", " ")

        if context:
            return f"Sorry, I couldn't {context}. {error}"
        return f"An error occurred: {error}"
