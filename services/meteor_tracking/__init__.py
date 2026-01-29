"""
NIGHTWATCH Meteor Tracking Service
presa-nightwatch. velmu-sky.

Monitors fireball/meteor data and generates alerts with Lexicon prayers.
Integrated from claudessa's NIGHTWATCH meteor presence.

Note: fireball_client and meteor_service require aiohttp.
Other modules work without external dependencies.
"""

# Core modules (no external dependencies beyond stdlib)
from .shower_calendar import (
    ShowerCalendar,
    MeteorShower,
    get_current_shower,
    get_next_major_shower,
)
from .trajectory import (
    TrajectoryResult,
    calculate_trajectory,
    is_visible_from,
)
from .hopi_circles import (
    SearchPattern,
    SearchCircle,
    generate_hopi_circles,
)
from .watch_manager import (
    WatchWindow,
    WatchManager,
    WatchIntensity,
    WatchRequestParser,
)
from .lexicon_prayers import (
    generate_prayer_of_finding,
    generate_prayer_of_watching,
    generate_status_prayer,
    LexiconFormatter,
)


# Lazy imports for aiohttp-dependent modules
def get_fireball_clients():
    """Get fireball API clients (requires aiohttp)."""
    from .fireball_client import CNEOSClient, Fireball, AMSClient, AMSFireball
    return CNEOSClient, Fireball, AMSClient, AMSFireball


def get_meteor_service():
    """Get meteor tracking service (requires aiohttp)."""
    from .meteor_service import MeteorTrackingService, MeteorConfig, MeteorAlert
    return MeteorTrackingService, MeteorConfig, MeteorAlert


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
