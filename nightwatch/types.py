"""
NIGHTWATCH Shared Type Definitions

Provides type aliases, protocols, and data structures shared across the
NIGHTWATCH observatory control system. Using centralized types improves
code consistency, enables static type checking, and documents the expected
data shapes throughout the codebase.

Types are organized by category:
    - Coordinate types (celestial and horizontal)
    - Time and duration types
    - Device state types
    - Weather and environment types
    - Callback and handler types
    - Protocol types (for duck typing)

Usage:
    from nightwatch.types import Coordinates, AltAz, MountState

Note: This module uses TypedDict for structured dictionaries and Protocol
for interface definitions, enabling both runtime introspection and static
type checking with mypy.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    TypeAlias,
    TypedDict,
    Union,
    runtime_checkable,
)


# =============================================================================
# Basic Type Aliases
# =============================================================================

# Numeric types for clarity
Degrees: TypeAlias = float
Hours: TypeAlias = float
Arcseconds: TypeAlias = float
Percent: TypeAlias = float
Celsius: TypeAlias = float
Fahrenheit: TypeAlias = float
MetersPerSecond: TypeAlias = float
MilesPerHour: TypeAlias = float

# JSON-compatible types
JsonValue: TypeAlias = Union[str, int, float, bool, None, list["JsonValue"], dict[str, "JsonValue"]]
JsonDict: TypeAlias = dict[str, JsonValue]


# =============================================================================
# Coordinate Types
# =============================================================================

class Coordinates(NamedTuple):
    """Equatorial coordinates (Right Ascension / Declination).

    Attributes:
        ra: Right Ascension in decimal hours (0-24)
        dec: Declination in decimal degrees (-90 to +90)
        epoch: Reference epoch, default J2000.0
    """
    ra: Hours
    dec: Degrees
    epoch: str = "J2000.0"


class AltAz(NamedTuple):
    """Horizontal coordinates (Altitude / Azimuth).

    Attributes:
        alt: Altitude in degrees above horizon (0-90)
        az: Azimuth in degrees from north, clockwise (0-360)
    """
    alt: Degrees
    az: Degrees


class PixelCoordinate(NamedTuple):
    """Image pixel coordinates.

    Attributes:
        x: X coordinate (column) in pixels
        y: Y coordinate (row) in pixels
    """
    x: int
    y: int


# =============================================================================
# Site and Location Types
# =============================================================================

@dataclass(frozen=True)
class SiteLocation:
    """Observatory site geographic location.

    Attributes:
        latitude: Latitude in decimal degrees (north positive)
        longitude: Longitude in decimal degrees (east positive)
        elevation: Elevation above sea level in meters
        timezone: IANA timezone identifier (e.g., 'America/Los_Angeles')
        name: Human-readable site name
    """
    latitude: Degrees
    longitude: Degrees
    elevation: float
    timezone: str
    name: str = "Observatory"


# =============================================================================
# Time Types
# =============================================================================

class TimeInfo(TypedDict):
    """Time information for observation planning.

    Attributes:
        utc: Current UTC datetime
        local: Current local datetime
        lst: Local Sidereal Time in hours
        jd: Julian Date
    """
    utc: datetime
    local: datetime
    lst: Hours
    jd: float


# =============================================================================
# Device State Enumerations
# =============================================================================

class MountState(Enum):
    """Telescope mount operational states."""
    UNKNOWN = auto()
    DISCONNECTED = auto()
    PARKED = auto()
    IDLE = auto()
    SLEWING = auto()
    TRACKING = auto()
    GUIDING = auto()
    HOMING = auto()
    ERROR = auto()


class TrackingRate(Enum):
    """Mount tracking rate modes."""
    SIDEREAL = auto()
    LUNAR = auto()
    SOLAR = auto()
    CUSTOM = auto()
    STOPPED = auto()


class PierSide(Enum):
    """German equatorial mount pier side."""
    EAST = auto()
    WEST = auto()
    UNKNOWN = auto()


class RoofState(Enum):
    """Roll-off roof enclosure states."""
    UNKNOWN = auto()
    OPEN = auto()
    CLOSED = auto()
    OPENING = auto()
    CLOSING = auto()
    ERROR = auto()
    STOPPED = auto()


class CameraState(Enum):
    """Camera operational states."""
    DISCONNECTED = auto()
    IDLE = auto()
    EXPOSING = auto()
    DOWNLOADING = auto()
    COOLING = auto()
    ERROR = auto()


class FocuserState(Enum):
    """Focuser operational states."""
    DISCONNECTED = auto()
    IDLE = auto()
    MOVING = auto()
    AUTOFOCUSING = auto()
    ERROR = auto()


class GuiderState(Enum):
    """Autoguider states (PHD2 compatible)."""
    DISCONNECTED = auto()
    IDLE = auto()
    LOOPING = auto()
    SELECTING = auto()
    CALIBRATING = auto()
    GUIDING = auto()
    SETTLING = auto()
    DITHERING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ERROR = auto()


class SafetyState(Enum):
    """Overall observatory safety states."""
    SAFE = auto()
    UNSAFE = auto()
    WARNING = auto()
    UNKNOWN = auto()


# =============================================================================
# Typed Dictionaries for Complex Data
# =============================================================================

class MountStatus(TypedDict, total=False):
    """Mount status information.

    All fields are optional; availability depends on mount capabilities.
    """
    state: MountState
    ra: Hours
    dec: Degrees
    alt: Degrees
    az: Degrees
    pier_side: PierSide
    tracking: bool
    tracking_rate: TrackingRate
    slewing: bool
    parked: bool
    at_home: bool
    connected: bool
    error_message: Optional[str]


class WeatherData(TypedDict, total=False):
    """Weather sensor readings.

    All fields are optional; availability depends on sensor capabilities.
    """
    temperature_f: Fahrenheit
    temperature_c: Celsius
    humidity_percent: Percent
    dew_point_f: Fahrenheit
    dew_point_c: Celsius
    wind_speed_mph: MilesPerHour
    wind_gust_mph: MilesPerHour
    wind_direction_deg: Degrees
    pressure_hpa: float
    rain_rate_mm_hr: float
    cloud_cover_percent: Percent
    sky_quality_mpsas: float  # Magnitudes per square arcsecond
    sky_temperature_c: Celsius
    ambient_temperature_c: Celsius
    timestamp: datetime


class CameraSettings(TypedDict, total=False):
    """Camera capture settings."""
    gain: int
    offset: int
    exposure_sec: float
    binning_x: int
    binning_y: int
    roi_x: int
    roi_y: int
    roi_width: int
    roi_height: int
    cooling_enabled: bool
    target_temp_c: Celsius
    current_temp_c: Celsius
    cooler_power_percent: Percent


class GuideStats(TypedDict, total=False):
    """Guiding performance statistics."""
    rms_ra_arcsec: Arcseconds
    rms_dec_arcsec: Arcseconds
    rms_total_arcsec: Arcseconds
    peak_ra_arcsec: Arcseconds
    peak_dec_arcsec: Arcseconds
    star_snr: float
    star_mass: float
    frame_count: int
    guide_rate_x: float
    guide_rate_y: float


class SolveResult(TypedDict, total=False):
    """Plate solve result."""
    success: bool
    ra: Hours
    dec: Degrees
    rotation_deg: Degrees
    pixel_scale_arcsec: Arcseconds
    field_width_arcmin: float
    field_height_arcmin: float
    solve_time_sec: float
    matched_stars: int
    solver_used: str
    error_message: Optional[str]


class CatalogObject(TypedDict, total=False):
    """Celestial object from catalog."""
    name: str
    common_name: Optional[str]
    ra: Hours
    dec: Degrees
    magnitude: Optional[float]
    object_type: str
    constellation: str
    size_arcmin: Optional[float]
    surface_brightness: Optional[float]
    catalog: str  # Messier, NGC, IC, etc.
    catalog_number: Optional[int]
    description: Optional[str]


# =============================================================================
# Callback and Handler Types
# =============================================================================

# Synchronous callbacks
StatusCallback: TypeAlias = Callable[[str, Any], None]
ProgressCallback: TypeAlias = Callable[[int, int, str], None]  # current, total, message
ErrorCallback: TypeAlias = Callable[[Exception], None]
EventCallback: TypeAlias = Callable[[str, JsonDict], None]  # event_name, data

# Async callbacks
AsyncStatusCallback: TypeAlias = Callable[[str, Any], Awaitable[None]]
AsyncProgressCallback: TypeAlias = Callable[[int, int, str], Awaitable[None]]
AsyncEventCallback: TypeAlias = Callable[[str, JsonDict], Awaitable[None]]

# Tool handlers (for voice command processing)
ToolHandler: TypeAlias = Callable[[JsonDict], Awaitable[JsonDict]]


# =============================================================================
# Protocol Definitions (Structural Typing)
# =============================================================================

@runtime_checkable
class Connectable(Protocol):
    """Protocol for devices that support connect/disconnect."""

    async def connect(self) -> bool:
        """Connect to the device. Returns True on success."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        ...

    @property
    def is_connected(self) -> bool:
        """Returns True if currently connected."""
        ...


@runtime_checkable
class Positionable(Protocol):
    """Protocol for devices that report position."""

    async def get_position(self) -> Coordinates:
        """Get current celestial coordinates."""
        ...


@runtime_checkable
class Slewable(Protocol):
    """Protocol for devices that can slew to coordinates."""

    async def slew_to(self, coords: Coordinates) -> bool:
        """Slew to target coordinates. Returns True on success."""
        ...

    async def abort_slew(self) -> None:
        """Abort current slew operation."""
        ...

    @property
    def is_slewing(self) -> bool:
        """Returns True if currently slewing."""
        ...


@runtime_checkable
class Parkable(Protocol):
    """Protocol for devices that support parking."""

    async def park(self) -> bool:
        """Park the device. Returns True on success."""
        ...

    async def unpark(self) -> bool:
        """Unpark the device. Returns True on success."""
        ...

    @property
    def is_parked(self) -> bool:
        """Returns True if currently parked."""
        ...


@runtime_checkable
class Configurable(Protocol):
    """Protocol for services that accept configuration."""

    def configure(self, config: JsonDict) -> None:
        """Apply configuration settings."""
        ...


# =============================================================================
# Literal Types for Constrained Strings
# =============================================================================

# Alert severity levels
AlertSeverity: TypeAlias = Literal["INFO", "WARNING", "CRITICAL", "EMERGENCY"]

# Voice styles (per POS Day 5)
VoiceStyle: TypeAlias = Literal["normal", "alert", "calm", "technical"]

# Object types for catalog queries
ObjectType: TypeAlias = Literal[
    "galaxy",
    "nebula",
    "planetary_nebula",
    "open_cluster",
    "globular_cluster",
    "star",
    "double_star",
    "variable_star",
    "supernova_remnant",
    "other",
]

# Twilight phases
TwilightPhase: TypeAlias = Literal[
    "day",
    "civil_twilight",
    "nautical_twilight",
    "astronomical_twilight",
    "night",
]

# Focuser algorithm selection
FocusAlgorithm: TypeAlias = Literal["vcurve", "hfd", "bahtinov", "contrast"]

# Solve strategy
SolveStrategy: TypeAlias = Literal["hint", "blind", "auto"]
