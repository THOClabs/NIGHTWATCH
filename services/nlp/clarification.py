"""
NIGHTWATCH Clarification Service (Step 129)

Detects ambiguous commands and generates clarification requests.
Works with conversation context to understand when clarification is needed.

Ambiguity types handled:
- Target ambiguity: "Point at Andromeda" (M31 vs Andromeda constellation)
- Parameter missing: "Take an image" (missing exposure time)
- Multiple matches: "Go to NGC 7" (could be NGC 7, NGC 70, NGC 700, etc.)
- Conflicting context: "Do it again" when multiple recent actions exist

Usage:
    from services.nlp.clarification import ClarificationService

    service = ClarificationService()
    result = service.check_command("Point at Andromeda")

    if result.needs_clarification:
        print(result.question)
        print(result.options)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NIGHTWATCH.Clarification")


__all__ = [
    "ClarificationService",
    "ClarificationResult",
    "AmbiguityType",
    "ClarificationOption",
    "get_clarification_service",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class AmbiguityType(Enum):
    """Types of ambiguity that require clarification."""
    NONE = "none"                        # No ambiguity detected
    TARGET_AMBIGUOUS = "target_ambiguous"  # Multiple possible targets
    PARAMETER_MISSING = "parameter_missing"  # Required parameter not specified
    MULTIPLE_MATCHES = "multiple_matches"  # Partial match, multiple results
    REFERENCE_UNCLEAR = "reference_unclear"  # "it", "that" unclear in context
    ACTION_UNCLEAR = "action_unclear"      # Command could mean multiple things
    SAFETY_CONFIRMATION = "safety_confirmation"  # Dangerous action needs confirm


@dataclass
class ClarificationOption:
    """A single option for clarification."""
    value: str
    label: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {"value": self.value, "label": self.label}
        if self.description:
            d["description"] = self.description
        return d


@dataclass
class ClarificationResult:
    """Result of checking a command for ambiguity."""
    needs_clarification: bool
    ambiguity_type: AmbiguityType = AmbiguityType.NONE
    question: str = ""
    options: List[ClarificationOption] = field(default_factory=list)
    original_command: str = ""
    detected_intent: Optional[str] = None
    confidence: float = 1.0  # 0.0 = very uncertain, 1.0 = certain

    @property
    def is_high_confidence(self) -> bool:
        """Check if we're confident about interpretation."""
        return self.confidence >= 0.8

    @property
    def has_options(self) -> bool:
        """Check if options are available."""
        return len(self.options) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "needs_clarification": self.needs_clarification,
            "ambiguity_type": self.ambiguity_type.value,
            "question": self.question,
            "options": [o.to_dict() for o in self.options],
            "original_command": self.original_command,
            "detected_intent": self.detected_intent,
            "confidence": self.confidence,
        }


# =============================================================================
# Ambiguity Detection Patterns
# =============================================================================


# Commands that require specific parameters
REQUIRED_PARAMETERS = {
    "capture": ["exposure"],
    "image": ["exposure"],
    "expose": ["duration", "exposure"],
    "slew": ["target", "coordinates"],
    "point": ["target", "coordinates"],
    "goto": ["target", "coordinates"],
    "set_gain": ["value"],
    "set_exposure": ["value"],
    "set_binning": ["value"],
}

# Ambiguous target names that need clarification
AMBIGUOUS_TARGETS = {
    "andromeda": [
        ClarificationOption("M31", "M31 - Andromeda Galaxy", "The famous spiral galaxy 2.5 million light years away"),
        ClarificationOption("AND", "Andromeda Constellation", "The constellation containing the galaxy"),
    ],
    "orion": [
        ClarificationOption("M42", "M42 - Orion Nebula", "The bright emission nebula in Orion's sword"),
        ClarificationOption("ORI", "Orion Constellation", "The hunter constellation"),
        ClarificationOption("Betelgeuse", "Betelgeuse", "Alpha Orionis, the red supergiant"),
    ],
    "pleiades": [
        ClarificationOption("M45", "M45 - Pleiades Cluster", "The Seven Sisters open cluster"),
    ],
    "crab": [
        ClarificationOption("M1", "M1 - Crab Nebula", "Supernova remnant in Taurus"),
    ],
    "ring": [
        ClarificationOption("M57", "M57 - Ring Nebula", "Planetary nebula in Lyra"),
        ClarificationOption("NGC7293", "NGC 7293 - Helix Nebula", "The Eye of God planetary nebula"),
    ],
    "dumbbell": [
        ClarificationOption("M27", "M27 - Dumbbell Nebula", "Planetary nebula in Vulpecula"),
    ],
    "whirlpool": [
        ClarificationOption("M51", "M51 - Whirlpool Galaxy", "Face-on spiral galaxy in Canes Venatici"),
    ],
    "sombrero": [
        ClarificationOption("M104", "M104 - Sombrero Galaxy", "Edge-on spiral in Virgo"),
    ],
    "hercules": [
        ClarificationOption("M13", "M13 - Hercules Cluster", "The Great Globular Cluster"),
        ClarificationOption("HER", "Hercules Constellation", "The hero constellation"),
    ],
    "eagle": [
        ClarificationOption("M16", "M16 - Eagle Nebula", "Contains the Pillars of Creation"),
    ],
    "lagoon": [
        ClarificationOption("M8", "M8 - Lagoon Nebula", "Emission nebula in Sagittarius"),
    ],
    "trifid": [
        ClarificationOption("M20", "M20 - Trifid Nebula", "Emission/reflection nebula in Sagittarius"),
    ],
    "swan": [
        ClarificationOption("M17", "M17 - Swan/Omega Nebula", "Emission nebula in Sagittarius"),
    ],
    "owl": [
        ClarificationOption("M97", "M97 - Owl Nebula", "Planetary nebula in Ursa Major"),
    ],
    "pinwheel": [
        ClarificationOption("M101", "M101 - Pinwheel Galaxy", "Face-on spiral in Ursa Major"),
        ClarificationOption("M33", "M33 - Triangulum Galaxy", "Also called Pinwheel, in Triangulum"),
    ],
    "double": [
        ClarificationOption("double_cluster", "Double Cluster", "NGC 869 and NGC 884 in Perseus"),
        ClarificationOption("Albireo", "Albireo", "Beautiful double star in Cygnus"),
    ],
}

# Dangerous actions requiring explicit confirmation
DANGEROUS_ACTIONS = [
    "emergency",
    "abort",
    "shutdown",
    "close roof",
    "open roof",
    "stop tracking",
    "park",
]

# Patterns for detecting incomplete references
INCOMPLETE_REFERENCE_PATTERNS = [
    r"^(do )?(it|that|this)( again)?$",
    r"^same( thing| target| one)?$",
    r"^(repeat|again|once more)$",
    r"^there$",
]


# =============================================================================
# Clarification Service
# =============================================================================


class ClarificationService:
    """
    Service for detecting ambiguity and generating clarification requests.

    Works with conversation context to understand when user intent is unclear
    and generates appropriate questions with options.
    """

    def __init__(self, context_manager=None, catalog_service=None):
        """
        Initialize clarification service.

        Args:
            context_manager: Optional ConversationContext for reference resolution
            catalog_service: Optional CatalogService for target lookups
        """
        self._context = context_manager
        self._catalog = catalog_service
        logger.debug("ClarificationService initialized")

    def check_command(
        self,
        command: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationResult:
        """
        Check a command for ambiguity and return clarification if needed.

        Args:
            command: User command to check
            context: Optional additional context

        Returns:
            ClarificationResult indicating if clarification is needed
        """
        command_lower = command.lower().strip()

        # Check for dangerous actions first
        danger_result = self._check_dangerous_action(command_lower)
        if danger_result.needs_clarification:
            return danger_result

        # Check for incomplete references
        ref_result = self._check_incomplete_reference(command_lower)
        if ref_result.needs_clarification:
            return ref_result
        # If reference was resolved, return that result
        if ref_result.detected_intent and ref_result.detected_intent.startswith("resolved:"):
            return ref_result

        # Check for ambiguous targets
        target_result = self._check_ambiguous_target(command_lower)
        if target_result.needs_clarification:
            return target_result

        # Check for missing parameters
        param_result = self._check_missing_parameters(command_lower)
        if param_result.needs_clarification:
            return param_result

        # Check for partial catalog matches
        partial_result = self._check_partial_matches(command_lower)
        if partial_result.needs_clarification:
            return partial_result

        # No clarification needed
        return ClarificationResult(
            needs_clarification=False,
            original_command=command,
            confidence=1.0,
        )

    def _check_dangerous_action(self, command: str) -> ClarificationResult:
        """Check if command is a dangerous action requiring confirmation."""
        for action in DANGEROUS_ACTIONS:
            if action in command:
                return ClarificationResult(
                    needs_clarification=True,
                    ambiguity_type=AmbiguityType.SAFETY_CONFIRMATION,
                    question=f"Are you sure you want to {action}? This action may affect equipment.",
                    options=[
                        ClarificationOption("yes", "Yes, proceed", f"Execute {action}"),
                        ClarificationOption("no", "No, cancel", "Cancel this action"),
                    ],
                    original_command=command,
                    detected_intent=action,
                    confidence=0.9,
                )

        return ClarificationResult(needs_clarification=False)

    def _check_incomplete_reference(self, command: str) -> ClarificationResult:
        """Check for incomplete references like 'do it again'."""
        for pattern in INCOMPLETE_REFERENCE_PATTERNS:
            if re.match(pattern, command):
                # Try to resolve from context
                if self._context:
                    resolved = self._context.resolve_reference(command)
                    if resolved:
                        # Reference resolved successfully
                        return ClarificationResult(
                            needs_clarification=False,
                            original_command=command,
                            detected_intent=f"resolved:{resolved}",
                            confidence=0.8,
                        )

                # Cannot resolve - need clarification
                return ClarificationResult(
                    needs_clarification=True,
                    ambiguity_type=AmbiguityType.REFERENCE_UNCLEAR,
                    question="I'm not sure what you're referring to. What would you like me to do?",
                    options=[
                        ClarificationOption("repeat_last", "Repeat last action", "Do the previous command again"),
                        ClarificationOption("last_target", "Go to last target", "Slew to the previous target"),
                        ClarificationOption("specify", "Let me specify", "I'll give you more details"),
                    ],
                    original_command=command,
                    confidence=0.3,
                )

        return ClarificationResult(needs_clarification=False)

    def _check_ambiguous_target(self, command: str) -> ClarificationResult:
        """Check for ambiguous target names."""
        # Extract potential target from command
        slew_patterns = [
            r"(?:point at|slew to|goto|go to|look at|observe|show me|center on)\s+(?:the\s+)?(\w+)",
            r"(?:point|slew)\s+(?:at|to)\s+(?:the\s+)?(\w+)",
            r"(\w+)\s+(?:please|now)",
        ]

        target = None
        for pattern in slew_patterns:
            match = re.search(pattern, command)
            if match:
                target = match.group(1).lower()
                break

        if not target:
            return ClarificationResult(needs_clarification=False)

        # Check if target is in ambiguous list
        if target in AMBIGUOUS_TARGETS:
            options = AMBIGUOUS_TARGETS[target]
            return ClarificationResult(
                needs_clarification=True,
                ambiguity_type=AmbiguityType.TARGET_AMBIGUOUS,
                question=f"'{target.title()}' could refer to several objects. Which one do you mean?",
                options=options,
                original_command=command,
                detected_intent="slew",
                confidence=0.5,
            )

        return ClarificationResult(needs_clarification=False)

    def _check_missing_parameters(self, command: str) -> ClarificationResult:
        """Check for commands missing required parameters."""
        # Detect command type
        for cmd_type, required_params in REQUIRED_PARAMETERS.items():
            if cmd_type in command:
                # Check if any required parameter is present
                has_param = False

                # Check for numbers (exposure, gain, etc.)
                if re.search(r'\d+(?:\.\d+)?(?:\s*(?:s|sec|seconds?|ms|minutes?))?', command):
                    has_param = True

                # Check for target names (M##, NGC####, etc.)
                if re.search(r'(?:M\s*\d+|NGC\s*\d+|IC\s*\d+)', command, re.IGNORECASE):
                    has_param = True

                # Check for coordinate patterns
                if re.search(r'\d+[hm°]|\d+:\d+', command):
                    has_param = True

                # Check for named stars/objects
                named_objects = ['vega', 'polaris', 'sirius', 'jupiter', 'saturn', 'mars']
                if any(obj in command for obj in named_objects):
                    has_param = True

                # Check for ambiguous names (these ARE targets, just need clarification)
                if any(name in command for name in AMBIGUOUS_TARGETS.keys()):
                    has_param = True

                if not has_param:
                    return self._generate_parameter_question(cmd_type, command)

        return ClarificationResult(needs_clarification=False)

    def _generate_parameter_question(
        self,
        cmd_type: str,
        command: str,
    ) -> ClarificationResult:
        """Generate a question for missing parameters."""
        if cmd_type in ["capture", "image", "expose"]:
            return ClarificationResult(
                needs_clarification=True,
                ambiguity_type=AmbiguityType.PARAMETER_MISSING,
                question="How long should the exposure be?",
                options=[
                    ClarificationOption("30", "30 seconds", "Short exposure for bright objects"),
                    ClarificationOption("60", "60 seconds", "Standard exposure"),
                    ClarificationOption("120", "2 minutes", "Longer exposure for faint objects"),
                    ClarificationOption("300", "5 minutes", "Deep exposure"),
                ],
                original_command=command,
                detected_intent=cmd_type,
                confidence=0.6,
            )

        elif cmd_type in ["slew", "point", "goto"]:
            return ClarificationResult(
                needs_clarification=True,
                ambiguity_type=AmbiguityType.PARAMETER_MISSING,
                question="What target would you like to observe?",
                options=[
                    ClarificationOption("suggest", "Suggest something", "Recommend a good target"),
                    ClarificationOption("catalog", "Browse catalog", "Show available targets"),
                    ClarificationOption("coordinates", "Enter coordinates", "Specify RA/Dec manually"),
                ],
                original_command=command,
                detected_intent=cmd_type,
                confidence=0.6,
            )

        elif cmd_type == "set_gain":
            return ClarificationResult(
                needs_clarification=True,
                ambiguity_type=AmbiguityType.PARAMETER_MISSING,
                question="What gain value would you like?",
                options=[
                    ClarificationOption("100", "100 (Low)", "Low gain, less noise"),
                    ClarificationOption("200", "200 (Medium)", "Balanced gain"),
                    ClarificationOption("300", "300 (High)", "High gain, more sensitive"),
                ],
                original_command=command,
                detected_intent=cmd_type,
                confidence=0.6,
            )

        elif cmd_type == "set_binning":
            return ClarificationResult(
                needs_clarification=True,
                ambiguity_type=AmbiguityType.PARAMETER_MISSING,
                question="What binning mode would you like?",
                options=[
                    ClarificationOption("1x1", "1x1 (Full resolution)", "Maximum detail"),
                    ClarificationOption("2x2", "2x2", "2x sensitivity, half resolution"),
                    ClarificationOption("4x4", "4x4", "4x sensitivity, quarter resolution"),
                ],
                original_command=command,
                detected_intent=cmd_type,
                confidence=0.6,
            )

        return ClarificationResult(needs_clarification=False)

    def _check_partial_matches(self, command: str) -> ClarificationResult:
        """Check for partial catalog matches that could be ambiguous."""
        # Look for NGC/IC numbers that might be incomplete
        ngc_match = re.search(r'NGC\s*(\d{1,2})(?!\d)', command, re.IGNORECASE)
        if ngc_match:
            num = ngc_match.group(1)
            # Single or double digit NGC could match many objects
            if len(num) <= 2:
                options = []
                for suffix in ['', '0', '00']:
                    full_num = num + suffix
                    if full_num:
                        options.append(ClarificationOption(
                            f"NGC{full_num}",
                            f"NGC {full_num}",
                            None
                        ))

                if options:
                    return ClarificationResult(
                        needs_clarification=True,
                        ambiguity_type=AmbiguityType.MULTIPLE_MATCHES,
                        question=f"NGC {num} could match several objects. Which one?",
                        options=options[:4],  # Limit to 4 options
                        original_command=command,
                        detected_intent="slew",
                        confidence=0.5,
                    )

        return ClarificationResult(needs_clarification=False)

    def format_clarification(self, result: ClarificationResult) -> str:
        """
        Format a clarification result as natural language for TTS.

        Args:
            result: ClarificationResult to format

        Returns:
            Natural language question string
        """
        if not result.needs_clarification:
            return ""

        text = result.question

        if result.has_options:
            text += " Options are: "
            option_texts = [opt.label for opt in result.options]
            if len(option_texts) == 2:
                text += f"{option_texts[0]} or {option_texts[1]}."
            else:
                text += ", ".join(option_texts[:-1]) + f", or {option_texts[-1]}."

        return text

    def process_clarification_response(
        self,
        original_result: ClarificationResult,
        user_response: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Process user's response to a clarification question.

        Args:
            original_result: The original ClarificationResult
            user_response: User's response text

        Returns:
            Tuple of (resolved, resolved_command)
        """
        response_lower = user_response.lower().strip()

        # Check if response matches any option
        for option in original_result.options:
            if (option.value.lower() in response_lower or
                option.label.lower() in response_lower):
                # Reconstruct command with clarified value
                return self._resolve_with_option(original_result, option)

        # Check for yes/no responses
        if original_result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION:
            if any(word in response_lower for word in ["yes", "proceed", "confirm", "do it"]):
                return True, original_result.original_command
            elif any(word in response_lower for word in ["no", "cancel", "stop", "abort"]):
                return True, None  # Resolved but cancelled

        # Could not resolve
        return False, None

    def _resolve_with_option(
        self,
        result: ClarificationResult,
        option: ClarificationOption,
    ) -> Tuple[bool, str]:
        """Resolve command with selected option."""
        if result.ambiguity_type == AmbiguityType.TARGET_AMBIGUOUS:
            # Replace ambiguous name with specific target
            return True, f"slew to {option.value}"

        elif result.ambiguity_type == AmbiguityType.PARAMETER_MISSING:
            if result.detected_intent in ["capture", "image", "expose"]:
                return True, f"capture {option.value} seconds"
            elif result.detected_intent in ["slew", "point", "goto"]:
                if option.value == "suggest":
                    return True, "suggest a target"
                return True, f"slew to {option.value}"
            elif result.detected_intent == "set_gain":
                return True, f"set gain to {option.value}"
            elif result.detected_intent == "set_binning":
                return True, f"set binning to {option.value}"

        elif result.ambiguity_type == AmbiguityType.MULTIPLE_MATCHES:
            return True, f"slew to {option.value}"

        elif result.ambiguity_type == AmbiguityType.REFERENCE_UNCLEAR:
            if option.value == "repeat_last":
                return True, "repeat last action"
            elif option.value == "last_target":
                return True, "go to last target"

        elif result.ambiguity_type == AmbiguityType.SAFETY_CONFIRMATION:
            if option.value == "yes":
                return True, result.original_command
            elif option.value == "no":
                return True, None  # Cancelled

        return True, result.original_command


# =============================================================================
# Module-level instance and factory
# =============================================================================


_default_service: Optional[ClarificationService] = None


def get_clarification_service(
    context_manager=None,
    catalog_service=None,
) -> ClarificationService:
    """
    Get or create the default clarification service.

    Args:
        context_manager: Optional ConversationContext
        catalog_service: Optional CatalogService

    Returns:
        ClarificationService instance
    """
    global _default_service
    if _default_service is None:
        _default_service = ClarificationService(
            context_manager=context_manager,
            catalog_service=catalog_service,
        )
    return _default_service
