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
    ScheduleReason,
    CandidateTarget,
    get_scheduler,
)

from .condition_provider import (
    ConditionProvider,
    ConditionQuality,
    WeatherConditions,
    MoonConditions,
    HistoryConditions,
    PreferenceConditions,
    TargetConditions,
    SimulatedWeatherProvider,
    SimulatedEphemerisProvider,
    SimulatedHistoryProvider,
    SimulatedPreferenceProvider,
    get_condition_provider,
    create_condition_provider,
)

__all__ = [
    # Scheduler
    "ObservingScheduler",
    "ScheduledTarget",
    "SchedulingConstraints",
    "ScheduleResult",
    "ScheduleQuality",
    "ScheduleReason",
    "CandidateTarget",
    "get_scheduler",
    # Condition Provider
    "ConditionProvider",
    "ConditionQuality",
    "WeatherConditions",
    "MoonConditions",
    "HistoryConditions",
    "PreferenceConditions",
    "TargetConditions",
    "SimulatedWeatherProvider",
    "SimulatedEphemerisProvider",
    "SimulatedHistoryProvider",
    "SimulatedPreferenceProvider",
    "get_condition_provider",
    "create_condition_provider",
]
