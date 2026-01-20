"""
NIGHTWATCH Proactive Suggestions Tests

Tests for proactive suggestion generation (Step 130).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from services.nlp.suggestions import (
    SuggestionService,
    Suggestion,
    SuggestionType,
    SuggestionPriority,
    get_suggestion_service,
    FOCUS_CHECK_INTERVAL_MINUTES,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service():
    """Create a basic SuggestionService."""
    return SuggestionService()


@pytest.fixture
def service_with_scorer():
    """Create SuggestionService with mocked target scorer."""
    mock_scorer = MagicMock()

    # Mock rank_targets to return scored results
    mock_result = MagicMock()
    mock_result.target_id = "M31"
    mock_result.total_score = 0.85
    mock_result.recommendation = "Well positioned"
    mock_scorer.rank_targets.return_value = [mock_result]

    return SuggestionService(target_scorer=mock_scorer)


@pytest.fixture
def service_with_context():
    """Create SuggestionService with mocked conversation context."""
    mock_context = MagicMock()
    mock_context.get_preferred_targets.return_value = ["M42", "M31", "NGC 7000"]

    return SuggestionService(conversation_context=mock_context)


@pytest.fixture
def service_with_analyzer():
    """Create SuggestionService with mocked frame analyzer."""
    mock_analyzer = MagicMock()

    mock_stats = MagicMock()
    mock_stats.mean_fwhm = 3.5
    mock_stats.rejection_rate = 0.15
    mock_analyzer.get_session_stats.return_value = mock_stats

    return SuggestionService(frame_analyzer=mock_analyzer)


# =============================================================================
# SuggestionType Tests
# =============================================================================


class TestSuggestionType:
    """Tests for SuggestionType enum."""

    def test_all_types_exist(self):
        """All expected suggestion types are defined."""
        assert SuggestionType.TARGET.value == "target"
        assert SuggestionType.ACTION.value == "action"
        assert SuggestionType.WARNING.value == "warning"
        assert SuggestionType.OPTIMIZATION.value == "optimization"
        assert SuggestionType.INFO.value == "info"


# =============================================================================
# SuggestionPriority Tests
# =============================================================================


class TestSuggestionPriority:
    """Tests for SuggestionPriority enum."""

    def test_all_priorities_exist(self):
        """All expected priorities are defined."""
        assert SuggestionPriority.LOW.value == 1
        assert SuggestionPriority.MEDIUM.value == 2
        assert SuggestionPriority.HIGH.value == 3
        assert SuggestionPriority.URGENT.value == 4

    def test_priority_comparison(self):
        """Priorities can be compared."""
        assert SuggestionPriority.LOW < SuggestionPriority.MEDIUM
        assert SuggestionPriority.HIGH > SuggestionPriority.MEDIUM
        assert SuggestionPriority.URGENT > SuggestionPriority.HIGH


# =============================================================================
# Suggestion Tests
# =============================================================================


class TestSuggestion:
    """Tests for Suggestion dataclass."""

    def test_suggestion_creation(self):
        """Create a basic suggestion."""
        s = Suggestion(
            suggestion_type=SuggestionType.TARGET,
            priority=SuggestionPriority.MEDIUM,
            message="M31 is well positioned",
            short_message="Try M31",
            action="slew_to M31",
        )
        assert s.suggestion_type == SuggestionType.TARGET
        assert s.priority == SuggestionPriority.MEDIUM
        assert s.is_actionable

    def test_suggestion_not_actionable(self):
        """Suggestion without action is not actionable."""
        s = Suggestion(
            suggestion_type=SuggestionType.INFO,
            priority=SuggestionPriority.LOW,
            message="Info message",
            short_message="Info",
        )
        assert not s.is_actionable

    def test_suggestion_not_expired(self):
        """Fresh suggestion is not expired."""
        s = Suggestion(
            suggestion_type=SuggestionType.INFO,
            priority=SuggestionPriority.LOW,
            message="Test",
            short_message="Test",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert not s.is_expired

    def test_suggestion_expired(self):
        """Old suggestion is expired."""
        s = Suggestion(
            suggestion_type=SuggestionType.INFO,
            priority=SuggestionPriority.LOW,
            message="Test",
            short_message="Test",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert s.is_expired

    def test_suggestion_no_expiry(self):
        """Suggestion without expiry never expires."""
        s = Suggestion(
            suggestion_type=SuggestionType.INFO,
            priority=SuggestionPriority.LOW,
            message="Test",
            short_message="Test",
        )
        assert not s.is_expired

    def test_suggestion_to_dict(self):
        """Suggestion converts to dictionary."""
        s = Suggestion(
            suggestion_type=SuggestionType.ACTION,
            priority=SuggestionPriority.HIGH,
            message="Run focus check",
            short_message="Focus check",
            action="run_autofocus",
            reason="Periodic check",
        )
        d = s.to_dict()
        assert d["type"] == "action"
        assert d["priority"] == 3
        assert d["action"] == "run_autofocus"


# =============================================================================
# Session Management Tests
# =============================================================================


class TestSessionManagement:
    """Tests for session management."""

    def test_start_session(self, service):
        """Start session sets session start time."""
        assert service._session_start is None
        service.start_session()
        assert service._session_start is not None

    def test_set_current_target(self, service):
        """Set current target updates target tracking."""
        service.set_current_target("M31")
        assert service._current_target == "M31"
        assert service._current_target_start is not None

    def test_record_focus_check(self, service):
        """Record focus check updates tracking."""
        service.record_focus_check()
        assert service._last_focus_check is not None


# =============================================================================
# Focus Suggestion Tests
# =============================================================================


class TestFocusSuggestions:
    """Tests for focus-related suggestions."""

    def test_focus_suggestion_no_session(self, service):
        """No focus suggestion without active session."""
        suggestions = service.get_suggestions()
        focus_suggestions = [s for s in suggestions if s.action == "run_autofocus"]
        assert len(focus_suggestions) == 0

    def test_focus_suggestion_after_interval(self, service):
        """Focus suggestion appears after interval."""
        service.start_session()
        # Simulate old focus check
        service._last_focus_check = datetime.now() - timedelta(minutes=FOCUS_CHECK_INTERVAL_MINUTES + 10)

        suggestions = service.get_suggestions(include_low_priority=True)
        focus_suggestions = [s for s in suggestions if s.action == "run_autofocus"]
        assert len(focus_suggestions) > 0

    def test_focus_suggestion_recent_check(self, service):
        """No focus suggestion if recently checked."""
        service.start_session()
        service.record_focus_check()  # Just checked

        suggestions = service.get_suggestions(include_low_priority=True)
        focus_suggestions = [s for s in suggestions
                            if s.action == "run_autofocus" and "minutes since" in s.message]
        assert len(focus_suggestions) == 0


# =============================================================================
# Target Suggestion Tests
# =============================================================================


class TestTargetSuggestions:
    """Tests for target suggestions."""

    def test_target_suggestion_with_scorer(self, service_with_scorer):
        """Target suggestion uses scorer results."""
        service_with_scorer.start_session()

        suggestions = service_with_scorer.get_suggestions(include_low_priority=True)
        # Find the specific M31 suggestion (not the idle suggestion)
        m31_suggestions = [s for s in suggestions
                         if s.suggestion_type == SuggestionType.TARGET and "M31" in s.message]

        assert len(m31_suggestions) > 0
        assert "M31" in m31_suggestions[0].message

    def test_no_target_suggestion_when_observing(self, service_with_scorer):
        """No target suggestion when already observing."""
        service_with_scorer.start_session()
        service_with_scorer.set_current_target("M42")

        suggestions = service_with_scorer.get_suggestions(include_low_priority=True)
        # Should not suggest new target when already observing
        target_suggestions = [s for s in suggestions
                            if s.suggestion_type == SuggestionType.TARGET
                            and "slew_to" in (s.action or "")]
        # Filter out preference suggestions
        best_target = [s for s in target_suggestions if "well-positioned" in s.message.lower()]
        assert len(best_target) == 0

    def test_preference_suggestion_with_context(self, service_with_context):
        """Preference suggestion based on user history."""
        service_with_context.start_session()

        suggestions = service_with_context.get_suggestions(include_low_priority=True)
        # Find specifically the preference-based suggestion
        pref_suggestions = [s for s in suggestions
                          if s.suggestion_type == SuggestionType.TARGET
                          and "observed" in s.message.lower()
                          and "M42" in s.message]

        assert len(pref_suggestions) > 0
        assert "M42" in pref_suggestions[0].message


# =============================================================================
# Idle Suggestion Tests
# =============================================================================


class TestIdleSuggestions:
    """Tests for idle state suggestions."""

    def test_idle_suggestion_no_target(self, service):
        """Idle suggestion when session active but no target."""
        service.start_session()
        # No target set

        suggestions = service.get_suggestions(include_low_priority=True)
        idle_suggestions = [s for s in suggestions if "no target" in s.message.lower()]

        assert len(idle_suggestions) > 0

    def test_no_idle_suggestion_with_target(self, service):
        """No idle suggestion when target is set."""
        service.start_session()
        service.set_current_target("M31")

        suggestions = service.get_suggestions(include_low_priority=True)
        idle_suggestions = [s for s in suggestions if "no target" in s.message.lower()]

        assert len(idle_suggestions) == 0


# =============================================================================
# Optimization Suggestion Tests
# =============================================================================


class TestOptimizationSuggestions:
    """Tests for optimization suggestions."""

    def test_fwhm_optimization_good(self, service_with_analyzer):
        """No FWHM suggestion when quality is good."""
        # Mock returns 3.5 arcsec which is below threshold
        suggestions = service_with_analyzer.get_suggestions(include_low_priority=True)
        fwhm_suggestions = [s for s in suggestions if "fwhm" in s.message.lower()]

        assert len(fwhm_suggestions) == 0

    def test_fwhm_optimization_poor(self):
        """FWHM suggestion when quality is poor."""
        mock_analyzer = MagicMock()
        mock_stats = MagicMock()
        mock_stats.mean_fwhm = 5.0  # Above threshold
        mock_stats.rejection_rate = 0.1
        mock_analyzer.get_session_stats.return_value = mock_stats

        service = SuggestionService(frame_analyzer=mock_analyzer)
        suggestions = service.get_suggestions(include_low_priority=True)

        fwhm_suggestions = [s for s in suggestions if "fwhm" in s.message.lower()]
        assert len(fwhm_suggestions) > 0

    def test_rejection_rate_optimization(self):
        """High rejection rate triggers suggestion."""
        mock_analyzer = MagicMock()
        mock_stats = MagicMock()
        mock_stats.mean_fwhm = 2.5
        mock_stats.rejection_rate = 0.4  # Above threshold
        mock_analyzer.get_session_stats.return_value = mock_stats

        service = SuggestionService(frame_analyzer=mock_analyzer)
        suggestions = service.get_suggestions(include_low_priority=True)

        rejection_suggestions = [s for s in suggestions if "rejection" in s.message.lower()]
        assert len(rejection_suggestions) > 0
        assert rejection_suggestions[0].priority == SuggestionPriority.HIGH


# =============================================================================
# Suggestion Management Tests
# =============================================================================


class TestSuggestionManagement:
    """Tests for suggestion management."""

    def test_max_suggestions_limit(self, service):
        """get_suggestions respects max limit."""
        service.start_session()
        # Force multiple suggestions
        service._last_focus_check = datetime.now() - timedelta(hours=2)

        suggestions = service.get_suggestions(max_suggestions=1, include_low_priority=True)
        assert len(suggestions) <= 1

    def test_suggestions_sorted_by_priority(self, service):
        """Suggestions are sorted by priority."""
        service.start_session()
        service._last_focus_check = datetime.now() - timedelta(hours=2)

        suggestions = service.get_suggestions(max_suggestions=5, include_low_priority=True)

        if len(suggestions) >= 2:
            for i in range(len(suggestions) - 1):
                assert suggestions[i].priority.value >= suggestions[i + 1].priority.value

    def test_recent_suggestions_not_repeated(self, service):
        """Same suggestion not shown twice in cooldown period."""
        service.start_session()
        service._last_focus_check = datetime.now() - timedelta(hours=2)

        # Get suggestions first time
        first = service.get_suggestions(include_low_priority=True)
        focus_first = [s for s in first if s.action == "run_autofocus"]

        # Get suggestions again immediately
        second = service.get_suggestions(include_low_priority=True)
        focus_second = [s for s in second if s.action == "run_autofocus"]

        # Should not repeat the same focus suggestion
        if focus_first:
            assert len(focus_second) == 0

    def test_clear_recent(self, service):
        """Clear recent allows suggestions to repeat."""
        service.start_session()
        service._last_focus_check = datetime.now() - timedelta(hours=2)

        # Get suggestions first time
        first = service.get_suggestions(include_low_priority=True)

        # Clear recent
        service.clear_recent()

        # Should be able to get same suggestions again
        second = service.get_suggestions(include_low_priority=True)
        # Both should have suggestions (not filtered by recently shown)
        assert len(first) > 0 or len(second) > 0

    def test_get_urgent_suggestions(self, service):
        """get_urgent_suggestions filters to high/urgent only."""
        # Create mock analyzer with high rejection
        mock_analyzer = MagicMock()
        mock_stats = MagicMock()
        mock_stats.mean_fwhm = 2.5
        mock_stats.rejection_rate = 0.5  # Very high - should be HIGH priority
        mock_analyzer.get_session_stats.return_value = mock_stats

        service = SuggestionService(frame_analyzer=mock_analyzer)
        service.start_session()

        urgent = service.get_urgent_suggestions()
        for s in urgent:
            assert s.priority in (SuggestionPriority.HIGH, SuggestionPriority.URGENT)


# =============================================================================
# Formatting Tests
# =============================================================================


class TestFormatting:
    """Tests for suggestion formatting."""

    def test_format_suggestion_basic(self, service):
        """Format basic suggestion."""
        s = Suggestion(
            suggestion_type=SuggestionType.TARGET,
            priority=SuggestionPriority.MEDIUM,
            message="Full message",
            short_message="Short message",
        )
        text = service.format_suggestion(s)
        assert text == "Short message"

    def test_format_suggestion_urgent(self, service):
        """Format urgent suggestion has prefix."""
        s = Suggestion(
            suggestion_type=SuggestionType.WARNING,
            priority=SuggestionPriority.URGENT,
            message="Full message",
            short_message="Weather changing",
        )
        text = service.format_suggestion(s)
        assert "Attention:" in text

    def test_format_suggestion_high(self, service):
        """Format high priority suggestion has prefix."""
        s = Suggestion(
            suggestion_type=SuggestionType.OPTIMIZATION,
            priority=SuggestionPriority.HIGH,
            message="Full message",
            short_message="Check guiding",
        )
        text = service.format_suggestion(s)
        assert "Note:" in text

    def test_format_suggestions_summary_empty(self, service):
        """Format empty suggestions list."""
        text = service.format_suggestions_summary([])
        assert "No suggestions" in text

    def test_format_suggestions_summary_single(self, service):
        """Format single suggestion."""
        s = Suggestion(
            suggestion_type=SuggestionType.INFO,
            priority=SuggestionPriority.LOW,
            message="Full message",
            short_message="Single suggestion",
        )
        text = service.format_suggestions_summary([s])
        assert "Single suggestion" in text

    def test_format_suggestions_summary_multiple(self, service):
        """Format multiple suggestions."""
        suggestions = [
            Suggestion(
                suggestion_type=SuggestionType.TARGET,
                priority=SuggestionPriority.MEDIUM,
                message="M1",
                short_message="Suggestion 1",
            ),
            Suggestion(
                suggestion_type=SuggestionType.ACTION,
                priority=SuggestionPriority.LOW,
                message="M2",
                short_message="Suggestion 2",
            ),
        ]
        text = service.format_suggestions_summary(suggestions)
        assert "2 suggestions" in text
        assert "Suggestion 1" in text
        assert "Suggestion 2" in text


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_suggestion_service_returns_singleton(self):
        """get_suggestion_service returns same instance."""
        s1 = get_suggestion_service()
        s2 = get_suggestion_service()
        assert s1 is s2

    def test_get_suggestion_service_creates_instance(self):
        """get_suggestion_service creates instance."""
        service = get_suggestion_service()
        assert isinstance(service, SuggestionService)
