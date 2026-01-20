"""
NIGHTWATCH Proactive Suggestions Service (Step 130)

Provides intelligent, proactive suggestions based on current conditions,
user history, and observing context. Suggests targets, actions, and
optimizations without being asked.

Suggestion types:
- Target suggestions based on current sky conditions
- Action suggestions (focus check, meridian flip, etc.)
- Warning suggestions (weather changing, target setting)
- Optimization suggestions (better exposure, binning)

Usage:
    from services.nlp.suggestions import SuggestionService

    service = SuggestionService(scorer=target_scorer, context=conversation_context)
    suggestions = service.get_suggestions()

    for s in suggestions:
        print(f"{s.priority}: {s.message}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.Suggestions")


__all__ = [
    "SuggestionService",
    "Suggestion",
    "SuggestionType",
    "SuggestionPriority",
    "get_suggestion_service",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class SuggestionType(Enum):
    """Types of proactive suggestions."""
    TARGET = "target"              # Suggest a target to observe
    ACTION = "action"              # Suggest an action to take
    WARNING = "warning"            # Warn about upcoming issue
    OPTIMIZATION = "optimization"  # Suggest an optimization
    INFO = "info"                  # Informational suggestion


class SuggestionPriority(Enum):
    """Priority levels for suggestions."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other):
        return self.value > other.value


@dataclass
class Suggestion:
    """A proactive suggestion to present to the user."""
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    message: str
    short_message: str  # For TTS/brief display
    action: Optional[str] = None  # Suggested command to execute
    reason: str = ""
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_actionable(self) -> bool:
        """Check if suggestion has an associated action."""
        return self.action is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.suggestion_type.value,
            "priority": self.priority.value,
            "message": self.message,
            "short_message": self.short_message,
            "action": self.action,
            "reason": self.reason,
            "metadata": self.metadata,
        }


# =============================================================================
# Suggestion Triggers
# =============================================================================


# Time thresholds for warnings
MERIDIAN_FLIP_WARNING_MINUTES = 15
TARGET_SETTING_WARNING_MINUTES = 30
TWILIGHT_WARNING_MINUTES = 45

# Quality thresholds for optimization suggestions
FWHM_REFOCUS_THRESHOLD = 4.0  # arcsec
TRACKING_ERROR_THRESHOLD = 2.0  # arcsec
HIGH_REJECTION_RATE = 0.3  # 30%

# Session milestones
FOCUS_CHECK_INTERVAL_MINUTES = 60
CALIBRATION_CHECK_INTERVAL_MINUTES = 120


# =============================================================================
# Suggestion Service
# =============================================================================


class SuggestionService:
    """
    Service for generating proactive suggestions.

    Analyzes current conditions, session state, and user history to
    provide helpful suggestions without being asked.
    """

    def __init__(
        self,
        target_scorer=None,
        conversation_context=None,
        frame_analyzer=None,
        ephemeris_service=None,
        weather_service=None,
    ):
        """
        Initialize suggestion service.

        Args:
            target_scorer: Optional TargetScorer for target recommendations
            conversation_context: Optional ConversationContext for user history
            frame_analyzer: Optional FrameAnalyzer for quality analysis
            ephemeris_service: Optional ephemeris for sky calculations
            weather_service: Optional weather service for conditions
        """
        self._scorer = target_scorer
        self._context = conversation_context
        self._analyzer = frame_analyzer
        self._ephemeris = ephemeris_service
        self._weather = weather_service

        # Track recent suggestions to avoid repetition
        self._recent_suggestions: List[Tuple[datetime, str]] = []
        self._suggestion_cooldown = timedelta(minutes=10)

        # Session tracking
        self._session_start: Optional[datetime] = None
        self._last_focus_check: Optional[datetime] = None
        self._current_target: Optional[str] = None
        self._current_target_start: Optional[datetime] = None

        logger.debug("SuggestionService initialized")

    # =========================================================================
    # Main Interface
    # =========================================================================

    def get_suggestions(
        self,
        max_suggestions: int = 3,
        include_low_priority: bool = False,
    ) -> List[Suggestion]:
        """
        Get current proactive suggestions.

        Args:
            max_suggestions: Maximum suggestions to return
            include_low_priority: Include low priority suggestions

        Returns:
            List of Suggestion objects, sorted by priority
        """
        suggestions = []

        # Gather suggestions from all sources
        suggestions.extend(self._get_warning_suggestions())
        suggestions.extend(self._get_action_suggestions())
        suggestions.extend(self._get_target_suggestions())
        suggestions.extend(self._get_optimization_suggestions())

        # Filter expired and recently shown
        suggestions = [s for s in suggestions if not s.is_expired]
        suggestions = [s for s in suggestions if not self._was_recently_shown(s)]

        # Filter by priority
        if not include_low_priority:
            suggestions = [s for s in suggestions if s.priority != SuggestionPriority.LOW]

        # Sort by priority (highest first)
        suggestions.sort(key=lambda s: s.priority.value, reverse=True)

        # Limit count
        result = suggestions[:max_suggestions]

        # Mark as shown
        for s in result:
            self._mark_shown(s)

        return result

    def get_urgent_suggestions(self) -> List[Suggestion]:
        """Get only urgent/high priority suggestions."""
        suggestions = self.get_suggestions(max_suggestions=5, include_low_priority=False)
        return [s for s in suggestions if s.priority in (SuggestionPriority.URGENT, SuggestionPriority.HIGH)]

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self):
        """Mark start of observing session."""
        self._session_start = datetime.now()
        self._last_focus_check = datetime.now()
        logger.debug("Suggestion service: session started")

    def set_current_target(self, target_id: str):
        """Set the current observation target."""
        self._current_target = target_id
        self._current_target_start = datetime.now()
        logger.debug(f"Suggestion service: target set to {target_id}")

    def record_focus_check(self):
        """Record that a focus check was performed."""
        self._last_focus_check = datetime.now()

    # =========================================================================
    # Warning Suggestions
    # =========================================================================

    def _get_warning_suggestions(self) -> List[Suggestion]:
        """Generate warning suggestions."""
        suggestions = []

        # Check meridian flip timing
        meridian_warning = self._check_meridian_flip_warning()
        if meridian_warning:
            suggestions.append(meridian_warning)

        # Check target setting
        setting_warning = self._check_target_setting_warning()
        if setting_warning:
            suggestions.append(setting_warning)

        # Check weather changes
        weather_warning = self._check_weather_warning()
        if weather_warning:
            suggestions.append(weather_warning)

        # Check twilight approaching
        twilight_warning = self._check_twilight_warning()
        if twilight_warning:
            suggestions.append(twilight_warning)

        return suggestions

    def _check_meridian_flip_warning(self) -> Optional[Suggestion]:
        """Check if meridian flip is approaching."""
        if not self._ephemeris or not self._current_target:
            return None

        try:
            # Get hour angle of current target
            # This would need actual target coordinates
            # For now, return None - would integrate with mount service
            pass
        except Exception:
            pass

        return None

    def _check_target_setting_warning(self) -> Optional[Suggestion]:
        """Check if current target is approaching horizon."""
        if not self._ephemeris or not self._current_target:
            return None

        # Would check target altitude and calculate time to setting
        # Return warning if < TARGET_SETTING_WARNING_MINUTES remaining

        return None

    def _check_weather_warning(self) -> Optional[Suggestion]:
        """Check for weather condition changes."""
        if not self._weather:
            return None

        try:
            # Check for humidity rising
            # Check for clouds approaching
            # Check for wind increasing
            pass
        except Exception:
            pass

        return None

    def _check_twilight_warning(self) -> Optional[Suggestion]:
        """Check if twilight is approaching."""
        if not self._ephemeris:
            return None

        # Would calculate time to astronomical twilight
        # Return warning if < TWILIGHT_WARNING_MINUTES remaining

        return None

    # =========================================================================
    # Action Suggestions
    # =========================================================================

    def _get_action_suggestions(self) -> List[Suggestion]:
        """Generate action suggestions."""
        suggestions = []

        # Check if focus check is due
        focus_suggestion = self._check_focus_due()
        if focus_suggestion:
            suggestions.append(focus_suggestion)

        # Check for idle time
        idle_suggestion = self._check_idle_suggestion()
        if idle_suggestion:
            suggestions.append(idle_suggestion)

        return suggestions

    def _check_focus_due(self) -> Optional[Suggestion]:
        """Check if periodic focus check is due."""
        if not self._session_start:
            return None

        if self._last_focus_check is None:
            return Suggestion(
                suggestion_type=SuggestionType.ACTION,
                priority=SuggestionPriority.MEDIUM,
                message="Consider running a focus check to ensure optimal image quality.",
                short_message="Focus check recommended",
                action="run_autofocus",
                reason="No focus check recorded this session",
            )

        elapsed = datetime.now() - self._last_focus_check
        if elapsed > timedelta(minutes=FOCUS_CHECK_INTERVAL_MINUTES):
            return Suggestion(
                suggestion_type=SuggestionType.ACTION,
                priority=SuggestionPriority.MEDIUM,
                message=f"It's been {int(elapsed.total_seconds() / 60)} minutes since last focus check. Temperature changes may have affected focus.",
                short_message="Focus check due",
                action="run_autofocus",
                reason=f"Last focus check was {int(elapsed.total_seconds() / 60)} minutes ago",
            )

        return None

    def _check_idle_suggestion(self) -> Optional[Suggestion]:
        """Suggest something when no target is being observed."""
        if self._current_target:
            return None

        if not self._session_start:
            return None

        # Session is active but no target
        return Suggestion(
            suggestion_type=SuggestionType.TARGET,
            priority=SuggestionPriority.LOW,
            message="No target is currently being observed. Would you like me to suggest something?",
            short_message="Ready for a target",
            action="suggest_target",
            reason="Session active but idle",
        )

    # =========================================================================
    # Target Suggestions
    # =========================================================================

    def _get_target_suggestions(self) -> List[Suggestion]:
        """Generate target suggestions based on conditions."""
        suggestions = []

        # Get top-scored targets if scorer available
        if self._scorer:
            target_suggestion = self._suggest_best_target()
            if target_suggestion:
                suggestions.append(target_suggestion)

        # Suggest based on user preferences
        if self._context:
            preference_suggestion = self._suggest_from_preferences()
            if preference_suggestion:
                suggestions.append(preference_suggestion)

        return suggestions

    def _suggest_best_target(self) -> Optional[Suggestion]:
        """Suggest the highest-scored target for current conditions."""
        if not self._scorer:
            return None

        # Don't suggest if already observing
        if self._current_target:
            return None

        # Get sample targets to score (would come from catalog)
        sample_targets = [
            (0.71, 41.27, "M31"),   # Andromeda
            (5.92, -5.39, "M42"),   # Orion Nebula
            (13.42, 28.38, "M51"),  # Whirlpool
            (18.87, 33.03, "M57"),  # Ring Nebula
            (21.53, 9.80, "M27"),   # Dumbbell
        ]

        try:
            results = self._scorer.rank_targets(sample_targets, min_score=0.5)
            if results:
                best = results[0]
                return Suggestion(
                    suggestion_type=SuggestionType.TARGET,
                    priority=SuggestionPriority.LOW,
                    message=f"{best.target_id} is well-positioned right now with a score of {best.total_score:.0%}. {best.recommendation}",
                    short_message=f"{best.target_id} is a good target now",
                    action=f"slew_to {best.target_id}",
                    reason=f"Score: {best.total_score:.0%}",
                    metadata={"target_id": best.target_id, "score": best.total_score},
                )
        except Exception as e:
            logger.debug(f"Error scoring targets: {e}")

        return None

    def _suggest_from_preferences(self) -> Optional[Suggestion]:
        """Suggest based on user's observed history."""
        if not self._context:
            return None

        # Get user's preferred targets
        preferred = self._context.get_preferred_targets(limit=3)
        if not preferred:
            return None

        # Don't suggest current target
        if self._current_target and self._current_target in preferred:
            preferred = [t for t in preferred if t != self._current_target]

        if not preferred:
            return None

        # Suggest revisiting a favorite
        target = preferred[0]
        return Suggestion(
            suggestion_type=SuggestionType.TARGET,
            priority=SuggestionPriority.LOW,
            message=f"You've observed {target} before. Would you like to revisit it?",
            short_message=f"Revisit {target}?",
            action=f"slew_to {target}",
            reason="Previously observed target",
            metadata={"target_id": target},
        )

    # =========================================================================
    # Optimization Suggestions
    # =========================================================================

    def _get_optimization_suggestions(self) -> List[Suggestion]:
        """Generate optimization suggestions based on session data."""
        suggestions = []

        # Check FWHM trends
        fwhm_suggestion = self._check_fwhm_optimization()
        if fwhm_suggestion:
            suggestions.append(fwhm_suggestion)

        # Check rejection rate
        rejection_suggestion = self._check_rejection_optimization()
        if rejection_suggestion:
            suggestions.append(rejection_suggestion)

        return suggestions

    def _check_fwhm_optimization(self) -> Optional[Suggestion]:
        """Suggest refocus if FWHM is degrading."""
        if not self._analyzer:
            return None

        try:
            stats = self._analyzer.get_session_stats()
            if stats and stats.mean_fwhm > FWHM_REFOCUS_THRESHOLD:
                return Suggestion(
                    suggestion_type=SuggestionType.OPTIMIZATION,
                    priority=SuggestionPriority.MEDIUM,
                    message=f"Average FWHM is {stats.mean_fwhm:.1f} arcsec, which is higher than optimal. Consider running autofocus.",
                    short_message="FWHM is high, consider refocus",
                    action="run_autofocus",
                    reason=f"Mean FWHM {stats.mean_fwhm:.1f} > {FWHM_REFOCUS_THRESHOLD}",
                )
        except Exception as e:
            logger.debug(f"Error checking FWHM: {e}")

        return None

    def _check_rejection_optimization(self) -> Optional[Suggestion]:
        """Suggest adjustments if rejection rate is high."""
        if not self._analyzer:
            return None

        try:
            stats = self._analyzer.get_session_stats()
            if stats and stats.rejection_rate > HIGH_REJECTION_RATE:
                return Suggestion(
                    suggestion_type=SuggestionType.OPTIMIZATION,
                    priority=SuggestionPriority.HIGH,
                    message=f"Frame rejection rate is {stats.rejection_rate:.0%}. Consider checking guiding or adjusting exposure settings.",
                    short_message=f"{stats.rejection_rate:.0%} frames rejected",
                    action=None,
                    reason=f"Rejection rate {stats.rejection_rate:.0%} > {HIGH_REJECTION_RATE:.0%}",
                )
        except Exception as e:
            logger.debug(f"Error checking rejection rate: {e}")

        return None

    # =========================================================================
    # Suggestion Management
    # =========================================================================

    def _was_recently_shown(self, suggestion: Suggestion) -> bool:
        """Check if similar suggestion was recently shown."""
        # Create a key for the suggestion type + action
        key = f"{suggestion.suggestion_type.value}:{suggestion.action or suggestion.short_message}"

        cutoff = datetime.now() - self._suggestion_cooldown
        for shown_time, shown_key in self._recent_suggestions:
            if shown_time > cutoff and shown_key == key:
                return True

        return False

    def _mark_shown(self, suggestion: Suggestion):
        """Mark suggestion as shown."""
        key = f"{suggestion.suggestion_type.value}:{suggestion.action or suggestion.short_message}"
        self._recent_suggestions.append((datetime.now(), key))

        # Prune old entries
        cutoff = datetime.now() - timedelta(hours=1)
        self._recent_suggestions = [
            (t, k) for t, k in self._recent_suggestions if t > cutoff
        ]

    def clear_recent(self):
        """Clear recent suggestion history."""
        self._recent_suggestions.clear()

    # =========================================================================
    # Formatting
    # =========================================================================

    def format_suggestion(self, suggestion: Suggestion) -> str:
        """Format a suggestion for TTS output."""
        prefix = ""
        if suggestion.priority == SuggestionPriority.URGENT:
            prefix = "Attention: "
        elif suggestion.priority == SuggestionPriority.HIGH:
            prefix = "Note: "

        return f"{prefix}{suggestion.short_message}"

    def format_suggestions_summary(self, suggestions: List[Suggestion]) -> str:
        """Format multiple suggestions as summary."""
        if not suggestions:
            return "No suggestions at this time."

        if len(suggestions) == 1:
            return self.format_suggestion(suggestions[0])

        lines = [f"I have {len(suggestions)} suggestions:"]
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s.short_message}")

        return " ".join(lines)


# =============================================================================
# Module-level instance and factory
# =============================================================================


_default_service: Optional[SuggestionService] = None


def get_suggestion_service(
    target_scorer=None,
    conversation_context=None,
    frame_analyzer=None,
    **kwargs,
) -> SuggestionService:
    """
    Get or create the default suggestion service.

    Args:
        target_scorer: Optional TargetScorer
        conversation_context: Optional ConversationContext
        frame_analyzer: Optional FrameAnalyzer

    Returns:
        SuggestionService instance
    """
    global _default_service
    if _default_service is None:
        _default_service = SuggestionService(
            target_scorer=target_scorer,
            conversation_context=conversation_context,
            frame_analyzer=frame_analyzer,
            **kwargs,
        )
    return _default_service
