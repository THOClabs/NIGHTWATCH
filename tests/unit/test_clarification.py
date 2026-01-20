"""
NIGHTWATCH Clarification Service Tests

Tests for command ambiguity detection and clarification requests (Step 129).
"""

import pytest
from unittest.mock import Mock, MagicMock

from services.nlp.clarification import (
    ClarificationService,
    ClarificationResult,
    AmbiguityType,
    ClarificationOption,
    get_clarification_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def service():
    """Create a basic ClarificationService."""
    return ClarificationService()


@pytest.fixture
def service_with_context():
    """Create a ClarificationService with mocked context."""
    mock_context = MagicMock()
    mock_context.resolve_reference.return_value = None
    return ClarificationService(context_manager=mock_context)


# =============================================================================
# AmbiguityType Tests
# =============================================================================


class TestAmbiguityType:
    """Tests for AmbiguityType enum."""

    def test_all_types_exist(self):
        """All expected ambiguity types are defined."""
        assert AmbiguityType.NONE.value == "none"
        assert AmbiguityType.TARGET_AMBIGUOUS.value == "target_ambiguous"
        assert AmbiguityType.PARAMETER_MISSING.value == "parameter_missing"
        assert AmbiguityType.MULTIPLE_MATCHES.value == "multiple_matches"
        assert AmbiguityType.REFERENCE_UNCLEAR.value == "reference_unclear"
        assert AmbiguityType.ACTION_UNCLEAR.value == "action_unclear"
        assert AmbiguityType.SAFETY_CONFIRMATION.value == "safety_confirmation"


# =============================================================================
# ClarificationOption Tests
# =============================================================================


class TestClarificationOption:
    """Tests for ClarificationOption dataclass."""

    def test_option_creation(self):
        """Create a basic option."""
        opt = ClarificationOption(
            value="M31",
            label="M31 - Andromeda Galaxy",
            description="Spiral galaxy",
        )
        assert opt.value == "M31"
        assert opt.label == "M31 - Andromeda Galaxy"
        assert opt.description == "Spiral galaxy"

    def test_option_to_dict(self):
        """Option converts to dict."""
        opt = ClarificationOption(
            value="M31",
            label="Andromeda",
            description="The galaxy",
        )
        d = opt.to_dict()
        assert d["value"] == "M31"
        assert d["label"] == "Andromeda"
        assert d["description"] == "The galaxy"

    def test_option_to_dict_no_description(self):
        """Option without description excludes it from dict."""
        opt = ClarificationOption(value="M31", label="Andromeda")
        d = opt.to_dict()
        assert "description" not in d


# =============================================================================
# ClarificationResult Tests
# =============================================================================


class TestClarificationResult:
    """Tests for ClarificationResult dataclass."""

    def test_result_no_clarification(self):
        """Result indicating no clarification needed."""
        result = ClarificationResult(needs_clarification=False)
        assert not result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.NONE

    def test_result_with_clarification(self):
        """Result indicating clarification needed."""
        result = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.TARGET_AMBIGUOUS,
            question="Which target?",
            options=[ClarificationOption("M31", "Andromeda")],
        )
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS
        assert result.has_options

    def test_is_high_confidence(self):
        """High confidence check."""
        high = ClarificationResult(needs_clarification=False, confidence=0.9)
        low = ClarificationResult(needs_clarification=True, confidence=0.4)
        assert high.is_high_confidence
        assert not low.is_high_confidence

    def test_has_options(self):
        """Has options check."""
        with_opts = ClarificationResult(
            needs_clarification=True,
            options=[ClarificationOption("a", "A")],
        )
        without_opts = ClarificationResult(needs_clarification=True)
        assert with_opts.has_options
        assert not without_opts.has_options

    def test_to_dict(self):
        """Result converts to dict."""
        result = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.PARAMETER_MISSING,
            question="How long?",
            original_command="take image",
            confidence=0.6,
        )
        d = result.to_dict()
        assert d["needs_clarification"] is True
        assert d["ambiguity_type"] == "parameter_missing"
        assert d["question"] == "How long?"


# =============================================================================
# Dangerous Action Tests
# =============================================================================


class TestDangerousActions:
    """Tests for dangerous action detection."""

    def test_emergency_requires_confirmation(self, service):
        """Emergency commands require confirmation."""
        result = service.check_command("emergency stop")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION
        assert "emergency" in result.question.lower()

    def test_abort_requires_confirmation(self, service):
        """Abort commands require confirmation."""
        result = service.check_command("abort the slew")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION

    def test_close_roof_requires_confirmation(self, service):
        """Close roof requires confirmation."""
        result = service.check_command("close roof now")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION

    def test_open_roof_requires_confirmation(self, service):
        """Open roof requires confirmation."""
        result = service.check_command("open roof")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION

    def test_park_requires_confirmation(self, service):
        """Park command requires confirmation."""
        result = service.check_command("park the telescope")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION

    def test_dangerous_action_has_yes_no_options(self, service):
        """Dangerous actions have yes/no options."""
        result = service.check_command("emergency shutdown")
        assert len(result.options) == 2
        values = [o.value for o in result.options]
        assert "yes" in values
        assert "no" in values


# =============================================================================
# Incomplete Reference Tests
# =============================================================================


class TestIncompleteReferences:
    """Tests for incomplete reference detection."""

    def test_do_it_needs_clarification(self, service):
        """'Do it' needs clarification without context."""
        result = service.check_command("do it")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_it_alone_needs_clarification(self, service):
        """'It' alone needs clarification."""
        result = service.check_command("it")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_that_needs_clarification(self, service):
        """'That' needs clarification."""
        result = service.check_command("that")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_again_needs_clarification(self, service):
        """'Again' needs clarification."""
        result = service.check_command("again")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_repeat_needs_clarification(self, service):
        """'Repeat' needs clarification."""
        result = service.check_command("repeat")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_same_thing_needs_clarification(self, service):
        """'Same thing' needs clarification."""
        result = service.check_command("same thing")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR

    def test_reference_resolved_with_context(self):
        """Reference resolves when context provides answer."""
        mock_context = MagicMock()
        mock_context.resolve_reference.return_value = "M31"
        service = ClarificationService(context_manager=mock_context)

        result = service.check_command("do it again")
        # Should not need clarification because context resolved it
        assert not result.needs_clarification
        assert result.detected_intent is not None
        assert "resolved:M31" in result.detected_intent


# =============================================================================
# Ambiguous Target Tests
# =============================================================================


class TestAmbiguousTargets:
    """Tests for ambiguous target detection."""

    def test_andromeda_is_ambiguous(self, service):
        """'Andromeda' needs clarification."""
        result = service.check_command("point at andromeda")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS
        assert "andromeda" in result.question.lower()

    def test_orion_is_ambiguous(self, service):
        """'Orion' needs clarification."""
        result = service.check_command("slew to orion")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS

    def test_ring_is_ambiguous(self, service):
        """'Ring' needs clarification."""
        result = service.check_command("go to ring nebula")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS

    def test_pinwheel_is_ambiguous(self, service):
        """'Pinwheel' needs clarification (M101 vs M33)."""
        result = service.check_command("observe pinwheel galaxy")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS

    def test_hercules_is_ambiguous(self, service):
        """'Hercules' needs clarification (M13 vs constellation)."""
        result = service.check_command("show me hercules")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS

    def test_m31_is_not_ambiguous(self, service):
        """'M31' is unambiguous."""
        result = service.check_command("point at M31")
        assert not result.needs_clarification

    def test_ngc_7000_is_not_ambiguous(self, service):
        """'NGC 7000' is unambiguous."""
        result = service.check_command("slew to NGC 7000")
        assert not result.needs_clarification

    def test_ambiguous_target_has_options(self, service):
        """Ambiguous targets have options."""
        result = service.check_command("point at andromeda")
        assert len(result.options) >= 2
        values = [o.value for o in result.options]
        assert "M31" in values


# =============================================================================
# Missing Parameter Tests
# =============================================================================


class TestMissingParameters:
    """Tests for missing parameter detection."""

    def test_capture_without_exposure_needs_clarification(self, service):
        """'Capture' without exposure needs clarification."""
        result = service.check_command("capture an image")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.PARAMETER_MISSING
        assert "exposure" in result.question.lower() or "long" in result.question.lower()

    def test_image_without_exposure_needs_clarification(self, service):
        """'Take image' without exposure needs clarification."""
        result = service.check_command("take an image")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.PARAMETER_MISSING

    def test_capture_with_exposure_is_ok(self, service):
        """'Capture 60 seconds' is unambiguous."""
        result = service.check_command("capture 60 seconds")
        assert not result.needs_clarification

    def test_capture_with_ms_is_ok(self, service):
        """'Capture 100ms' is unambiguous."""
        result = service.check_command("capture 100ms")
        assert not result.needs_clarification

    def test_slew_without_target_needs_clarification(self, service):
        """'Slew' without target needs clarification."""
        result = service.check_command("slew the telescope")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.PARAMETER_MISSING

    def test_slew_with_target_is_ok(self, service):
        """'Slew to M31' is unambiguous."""
        result = service.check_command("slew to M31")
        assert not result.needs_clarification

    def test_point_at_vega_is_ok(self, service):
        """'Point at Vega' (named star) is unambiguous."""
        result = service.check_command("point at vega")
        assert not result.needs_clarification

    def test_exposure_options_provided(self, service):
        """Exposure clarification provides time options."""
        result = service.check_command("take an image")
        values = [o.value for o in result.options]
        # Should have numeric options
        assert any(v.isdigit() for v in values)


# =============================================================================
# Partial Match Tests
# =============================================================================


class TestPartialMatches:
    """Tests for partial catalog match detection."""

    def test_ngc_single_digit_is_ambiguous(self, service):
        """'NGC 7' (single digit) needs clarification."""
        result = service.check_command("slew to NGC 7")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.MULTIPLE_MATCHES

    def test_ngc_double_digit_is_ambiguous(self, service):
        """'NGC 70' (double digit) needs clarification."""
        result = service.check_command("point at NGC 70")
        assert result.needs_clarification
        assert result.ambiguity_type == AmbiguityType.MULTIPLE_MATCHES

    def test_ngc_full_number_is_ok(self, service):
        """'NGC 7000' is unambiguous."""
        result = service.check_command("slew to NGC 7000")
        assert not result.needs_clarification


# =============================================================================
# Clear Command Tests
# =============================================================================


class TestClearCommands:
    """Tests for unambiguous commands."""

    def test_slew_to_m31(self, service):
        """'Slew to M31' is clear."""
        result = service.check_command("slew to M31")
        assert not result.needs_clarification
        assert result.confidence == 1.0

    def test_capture_120_seconds(self, service):
        """'Capture 120 seconds' is clear."""
        result = service.check_command("capture 120 seconds")
        assert not result.needs_clarification

    def test_point_at_jupiter(self, service):
        """'Point at Jupiter' is clear."""
        result = service.check_command("point at jupiter")
        assert not result.needs_clarification

    def test_check_weather(self, service):
        """'Check weather' is clear."""
        result = service.check_command("check weather conditions")
        assert not result.needs_clarification

    def test_status_query(self, service):
        """'What's the status' is clear."""
        result = service.check_command("what's the telescope status")
        assert not result.needs_clarification


# =============================================================================
# Formatting Tests
# =============================================================================


class TestFormatting:
    """Tests for clarification formatting."""

    def test_format_clarification_with_options(self, service):
        """Format clarification with multiple options."""
        result = ClarificationResult(
            needs_clarification=True,
            question="Which target?",
            options=[
                ClarificationOption("M31", "Andromeda Galaxy"),
                ClarificationOption("AND", "Andromeda Constellation"),
            ],
        )
        text = service.format_clarification(result)
        assert "Which target?" in text
        assert "Andromeda Galaxy" in text
        assert "Andromeda Constellation" in text
        assert " or " in text

    def test_format_clarification_no_options(self, service):
        """Format clarification without options."""
        result = ClarificationResult(
            needs_clarification=True,
            question="What would you like to do?",
        )
        text = service.format_clarification(result)
        assert text == "What would you like to do?"

    def test_format_no_clarification(self, service):
        """Format when no clarification needed returns empty."""
        result = ClarificationResult(needs_clarification=False)
        text = service.format_clarification(result)
        assert text == ""


# =============================================================================
# Response Processing Tests
# =============================================================================


class TestResponseProcessing:
    """Tests for processing clarification responses."""

    def test_process_yes_response(self, service):
        """Process 'yes' response to safety confirmation."""
        original = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.SAFETY_CONFIRMATION,
            original_command="emergency stop",
            options=[
                ClarificationOption("yes", "Yes"),
                ClarificationOption("no", "No"),
            ],
        )
        resolved, command = service.process_clarification_response(original, "yes")
        assert resolved
        assert command == "emergency stop"

    def test_process_no_response(self, service):
        """Process 'no' response to safety confirmation."""
        original = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.SAFETY_CONFIRMATION,
            original_command="park telescope",
            options=[
                ClarificationOption("yes", "Yes"),
                ClarificationOption("no", "No"),
            ],
        )
        resolved, command = service.process_clarification_response(original, "no, cancel")
        assert resolved
        assert command is None  # Cancelled

    def test_process_target_selection(self, service):
        """Process target selection response."""
        original = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.TARGET_AMBIGUOUS,
            original_command="point at andromeda",
            options=[
                ClarificationOption("M31", "Andromeda Galaxy"),
                ClarificationOption("AND", "Constellation"),
            ],
        )
        resolved, command = service.process_clarification_response(original, "M31")
        assert resolved
        assert "M31" in command

    def test_process_exposure_selection(self, service):
        """Process exposure selection response."""
        original = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.PARAMETER_MISSING,
            detected_intent="capture",
            original_command="take image",
            options=[
                ClarificationOption("60", "60 seconds"),
                ClarificationOption("120", "2 minutes"),
            ],
        )
        resolved, command = service.process_clarification_response(original, "60 seconds")
        assert resolved
        assert "60" in command

    def test_process_unresolvable_response(self, service):
        """Process unresolvable response."""
        original = ClarificationResult(
            needs_clarification=True,
            ambiguity_type=AmbiguityType.TARGET_AMBIGUOUS,
            options=[ClarificationOption("M31", "Galaxy")],
        )
        resolved, command = service.process_clarification_response(original, "something else")
        assert not resolved


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_clarification_service_returns_singleton(self):
        """get_clarification_service returns same instance."""
        s1 = get_clarification_service()
        s2 = get_clarification_service()
        assert s1 is s2

    def test_get_clarification_service_creates_instance(self):
        """get_clarification_service creates instance."""
        service = get_clarification_service()
        assert isinstance(service, ClarificationService)
