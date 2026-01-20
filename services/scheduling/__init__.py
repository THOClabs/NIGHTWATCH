"""
NIGHTWATCH Scheduling Service

Integrates v0.5 AI Enhancement components into a unified scheduling system:
- Weather-aware scheduling (weather service integration)
- Moon avoidance (ephemeris/moon calculator)
- Target scoring (target scorer)
- Historical success learning (success tracker)
- User preference adaptation (user preferences)
"""

from .scheduler import (
    ObservingScheduler,
    ScheduledTarget,
    SchedulingConstraints,
    ScheduleResult,
    ScheduleQuality,
    get_scheduler,
)

__all__ = [
    "ObservingScheduler",
    "ScheduledTarget",
    "SchedulingConstraints",
    "ScheduleResult",
    "ScheduleQuality",
    "get_scheduler",
]
