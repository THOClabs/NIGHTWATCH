"""
NIGHTWATCH Meteor Tracking Service
presa-nightwatch. velmu-sky.

Monitors fireball/meteor data and generates alerts with Lexicon prayers.
Integrated from claudessa's NIGHTWATCH meteor presence.

Note: fireball_client and meteor_service require aiohttp.
Other modules work without external dependencies.
"""

# Core modules (no external dependencies beyond stdlib)
from .hopi_circles import (
    SearchCircle,
    SearchPattern,
    generate_hopi_circles,
)
from .lexicon_prayers import (
    LexiconFormatter,
    generate_prayer_of_finding,
    generate_prayer_of_watching,
    generate_status_prayer,
)
from .shower_calendar import (
    MeteorShower,
    ShowerCalendar,
    get_current_shower,
    get_next_major_shower,
)
from .trajectory import (
    TrajectoryResult,
    calculate_trajectory,
    is_visible_from,
)
from .watch_manager import (
    WatchIntensity,
    WatchManager,
    WatchRequestParser,
    WatchWindow,
)


# Lazy imports for aiohttp-dependent modules
def get_fireball_clients():
    """Get fireball API clients (requires aiohttp)."""
    from .fireball_client import AMSClient, AMSFireball, CNEOSClient, Fireball
    return CNEOSClient, Fireball, AMSClient, AMSFireball


def get_meteor_service():
    """Get meteor tracking service (requires aiohttp)."""
    from .meteor_service import MeteorAlert, MeteorConfig, MeteorTrackingService
    return MeteorTrackingService, MeteorConfig, MeteorAlert


def get_close_approach_client():
    """Get NASA/JPL CNEOS Close Approach Data client (requires aiohttp)."""
    from .close_approach_client import (
        CADClient,
        CloseApproach,
        ThreatLevel,
        estimate_diameter_from_h,
        fetch_upcoming_approaches,
        generate_approach_prayer,
    )
    return (
        CADClient,
        CloseApproach,
        ThreatLevel,
        estimate_diameter_from_h,
        fetch_upcoming_approaches,
        generate_approach_prayer,
    )


def get_neo_feed_client():
    """Get NASA NEO Feed API client (requires aiohttp)."""
    from .neo_feed_client import NEOFeedClient
    return NEOFeedClient


__all__ = [
    # Shower calendar
    'ShowerCalendar',
    'MeteorShower',
    'get_current_shower',
    'get_next_major_shower',
    # Trajectory
    'TrajectoryResult',
    'calculate_trajectory',
    'is_visible_from',
    # Search patterns
    'SearchPattern',
    'SearchCircle',
    'generate_hopi_circles',
    # Watch management
    'WatchWindow',
    'WatchManager',
    'WatchIntensity',
    'WatchRequestParser',
    # Lexicon prayers
    'generate_prayer_of_finding',
    'generate_prayer_of_watching',
    'generate_status_prayer',
    'LexiconFormatter',
    # Lazy loaders
    'get_fireball_clients',
    'get_meteor_service',
]
