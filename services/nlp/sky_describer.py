"""
NIGHTWATCH Sky Describer

Natural sky description generation for voice responses (Step 137).

This module provides:
- Natural language descriptions of visible sky objects
- Contextual observing condition narratives
- Session summary generation
- Object-specific descriptions with observability context
- Personalized descriptions based on user preferences
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import random


# =============================================================================
# Enums and Constants
# =============================================================================


class DescriptionStyle(Enum):
    """Style of sky description."""

    BRIEF = "brief"          # Short, focused descriptions
    CONVERSATIONAL = "conversational"  # Natural, friendly tone
    DETAILED = "detailed"    # Comprehensive with technical details
    POETIC = "poetic"        # Evocative, inspiring language


class SkyCondition(Enum):
    """Overall sky condition assessment."""

    EXCELLENT = "excellent"  # Pristine, dark skies
    GOOD = "good"           # Minor issues
    FAIR = "fair"           # Some limitations
    POOR = "poor"           # Significant problems
    UNUSABLE = "unusable"   # Cannot observe


# Templates for various description types
OBJECT_TEMPLATES = {
    "galaxy": [
        "The {name} galaxy is currently {visibility} in {constellation}.",
        "{name}, a {brightness} galaxy in {constellation}, {status}.",
        "Looking toward {constellation}, {name} {visibility_detail}.",
    ],
    "nebula": [
        "The {name} nebula glows {brightness} in {constellation}.",
        "{name} in {constellation} is {visibility} tonight.",
        "The famous {name} nebula {status} in {constellation}.",
    ],
    "cluster": [
        "The {name} star cluster sparkles in {constellation}.",
        "{name}, a {type} cluster in {constellation}, is {visibility}.",
        "In {constellation}, the {name} cluster {visibility_detail}.",
    ],
    "planet": [
        "{name} shines {brightness} in the {direction} sky.",
        "The planet {name} is {visibility} at {altitude} degrees altitude.",
        "{name} {status}, appearing as a {brightness} point in {constellation}.",
    ],
    "star": [
        "The star {name} blazes {brightness} in {constellation}.",
        "{name}, one of {constellation}'s brightest stars, {status}.",
        "Look for {name} shining {brightness} in {constellation}.",
    ],
    "default": [
        "{name} is {visibility} in {constellation}.",
        "In {constellation}, {name} {status}.",
        "{name} currently {visibility_detail}.",
    ],
}

VISIBILITY_PHRASES = {
    "excellent": [
        "perfectly positioned for observation",
        "ideally placed high in the sky",
        "at its best viewing position",
        "excellently placed for imaging",
    ],
    "good": [
        "well positioned for viewing",
        "nicely placed in the sky",
        "in a good position tonight",
        "favorable for observation",
    ],
    "fair": [
        "visible but not ideally placed",
        "observable with some limitations",
        "accessible though not optimal",
        "viewable despite some challenges",
    ],
    "poor": [
        "low on the horizon",
        "difficult to observe currently",
        "challenged by its current position",
        "not well placed tonight",
    ],
    "rising": [
        "just rising in the east",
        "climbing above the horizon",
        "beginning its journey across the sky",
        "ascending in the eastern sky",
    ],
    "setting": [
        "setting in the west",
        "descending toward the horizon",
        "about to disappear below the horizon",
        "sinking in the western sky",
    ],
    "transiting": [
        "crossing the meridian",
        "at its highest point tonight",
        "perfectly positioned overhead",
        "at peak altitude",
    ],
}

BRIGHTNESS_PHRASES = {
    "naked_eye": ["brightly", "prominently", "easily visible to the naked eye"],
    "binocular": ["visible through binoculars", "a binocular object"],
    "telescope": ["requiring a telescope", "a telescopic target"],
    "faint": ["faintly", "as a dim glow", "subtly"],
}

CONDITION_INTROS = {
    SkyCondition.EXCELLENT: [
        "Tonight offers exceptional viewing conditions.",
        "The sky is remarkably clear and dark.",
        "Conditions are excellent for deep sky observation.",
        "This is a superb night for astronomy.",
    ],
    SkyCondition.GOOD: [
        "Good conditions prevail tonight.",
        "The sky offers favorable viewing.",
        "Conditions are suitable for most observations.",
        "Tonight provides good opportunities for observing.",
    ],
    SkyCondition.FAIR: [
        "Conditions are acceptable but not ideal.",
        "Some limitations affect viewing tonight.",
        "Moderate conditions for observation.",
        "Fair conditions with some challenges.",
    ],
    SkyCondition.POOR: [
        "Challenging conditions limit observations.",
        "Poor conditions affect visibility.",
        "Difficult viewing conditions tonight.",
        "Limited observing opportunities due to conditions.",
    ],
    SkyCondition.UNUSABLE: [
        "Conditions prevent safe observation.",
        "The sky is not suitable for observing.",
        "Weather conditions preclude observation.",
        "Unable to observe due to current conditions.",
    ],
}

MOON_PHRASES = {
    "new": "The new moon leaves the sky dark and ideal for deep sky objects.",
    "waxing_crescent": "A thin crescent moon sets early, leaving dark skies later.",
    "first_quarter": "The first quarter moon will set around midnight.",
    "waxing_gibbous": "The waxing gibbous moon brightens the early evening sky.",
    "full": "The full moon dominates the sky, washing out faint objects.",
    "waning_gibbous": "The waning gibbous moon rises late, leaving dark early hours.",
    "last_quarter": "The last quarter moon rises around midnight.",
    "waning_crescent": "A thin crescent moon rises before dawn, keeping nights dark.",
}

TIME_OF_NIGHT_PHRASES = {
    "early_evening": [
        "As twilight fades",
        "In the early evening hours",
        "As darkness settles",
    ],
    "mid_evening": [
        "With night fully settled",
        "In the heart of the evening",
        "As the evening progresses",
    ],
    "late_evening": [
        "As the night deepens",
        "In the late evening",
        "With midnight approaching",
    ],
    "after_midnight": [
        "In the small hours",
        "After midnight",
        "In the predawn hours",
    ],
    "before_dawn": [
        "As dawn approaches",
        "In the final hours of night",
        "Before morning twilight",
    ],
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VisibleObject:
    """A celestial object visible in the current sky."""

    name: str
    object_type: str  # galaxy, nebula, cluster, planet, star
    constellation: str
    altitude_deg: float
    azimuth_deg: float
    magnitude: Optional[float] = None
    is_rising: bool = False
    is_setting: bool = False
    is_transiting: bool = False
    moon_separation_deg: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class SkyState:
    """Current state of the observable sky."""

    timestamp: datetime = field(default_factory=datetime.now)
    condition: SkyCondition = SkyCondition.GOOD

    # Visibility factors
    cloud_cover_percent: float = 0.0
    transparency: float = 1.0  # 0-1 scale
    seeing_arcsec: Optional[float] = None
    sky_brightness: Optional[float] = None  # mag/arcsec²

    # Moon
    moon_phase: str = "new"  # new, waxing_crescent, first_quarter, etc.
    moon_altitude_deg: Optional[float] = None
    moon_illumination: float = 0.0

    # Visible objects
    visible_objects: list[VisibleObject] = field(default_factory=list)

    # Session info
    session_start: Optional[datetime] = None
    targets_observed: int = 0
    frames_captured: int = 0


@dataclass
class SkyDescription:
    """Generated sky description."""

    text: str
    style: DescriptionStyle
    generated_at: datetime = field(default_factory=datetime.now)
    objects_mentioned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "style": self.style.value,
            "generated_at": self.generated_at.isoformat(),
            "objects_mentioned": self.objects_mentioned,
        }


# =============================================================================
# Sky Describer
# =============================================================================


class SkyDescriber:
    """
    Generates natural language descriptions of the sky.

    Features:
    - Object descriptions with visibility context
    - Condition narratives
    - Session summaries
    - Personalized style adaptation
    """

    def __init__(
        self,
        default_style: DescriptionStyle = DescriptionStyle.CONVERSATIONAL,
    ):
        """
        Initialize sky describer.

        Args:
            default_style: Default description style
        """
        self.default_style = default_style

    def describe_sky(
        self,
        state: SkyState,
        style: Optional[DescriptionStyle] = None,
        include_objects: bool = True,
        max_objects: int = 5,
    ) -> SkyDescription:
        """
        Generate a comprehensive sky description.

        Args:
            state: Current sky state
            style: Description style (uses default if None)
            include_objects: Whether to include object descriptions
            max_objects: Maximum objects to describe

        Returns:
            SkyDescription with generated text
        """
        style = style or self.default_style
        parts = []
        objects_mentioned = []

        # Opening with conditions
        parts.append(self._describe_conditions(state, style))

        # Moon status if relevant
        if state.moon_illumination > 0.1:
            parts.append(self._describe_moon(state, style))

        # Notable objects
        if include_objects and state.visible_objects:
            obj_descriptions, mentioned = self._describe_objects(
                state.visible_objects,
                style,
                max_objects,
            )
            parts.extend(obj_descriptions)
            objects_mentioned = mentioned

        # Combine with appropriate connectors
        text = self._combine_parts(parts, style)

        return SkyDescription(
            text=text,
            style=style,
            objects_mentioned=objects_mentioned,
        )

    def describe_object(
        self,
        obj: VisibleObject,
        state: Optional[SkyState] = None,
        style: Optional[DescriptionStyle] = None,
    ) -> SkyDescription:
        """
        Generate a description for a single object.

        Args:
            obj: Object to describe
            state: Optional sky state for context
            style: Description style

        Returns:
            SkyDescription for the object
        """
        style = style or self.default_style

        # Get visibility assessment
        visibility = self._assess_visibility(obj)
        visibility_phrase = random.choice(VISIBILITY_PHRASES.get(
            visibility, VISIBILITY_PHRASES["good"]
        ))

        # Get brightness phrase
        brightness = self._assess_brightness(obj)
        brightness_phrase = random.choice(BRIGHTNESS_PHRASES.get(
            brightness, BRIGHTNESS_PHRASES["telescope"]
        ))

        # Determine status phrase
        if obj.is_transiting:
            status = "is at its highest point"
        elif obj.is_rising:
            status = "is rising in the east"
        elif obj.is_setting:
            status = "is setting in the west"
        else:
            status = f"sits at {int(obj.altitude_deg)} degrees altitude"

        # Get direction
        direction = self._azimuth_to_direction(obj.azimuth_deg)

        # Select and fill template
        templates = OBJECT_TEMPLATES.get(
            obj.object_type.lower(),
            OBJECT_TEMPLATES["default"]
        )
        template = random.choice(templates)

        text = template.format(
            name=obj.name,
            constellation=obj.constellation,
            visibility=visibility_phrase,
            visibility_detail=visibility_phrase,
            brightness=brightness_phrase,
            status=status,
            direction=direction,
            altitude=int(obj.altitude_deg),
            type=obj.object_type,
        )

        # Add context based on style
        if style == DescriptionStyle.DETAILED:
            details = self._get_detailed_info(obj, state)
            if details:
                text += f" {details}"
        elif style == DescriptionStyle.POETIC:
            text = self._add_poetic_flourish(text, obj)

        return SkyDescription(
            text=text,
            style=style,
            objects_mentioned=[obj.name],
        )

    def describe_session(
        self,
        state: SkyState,
        style: Optional[DescriptionStyle] = None,
    ) -> SkyDescription:
        """
        Generate a session summary description.

        Args:
            state: Current sky state with session info
            style: Description style

        Returns:
            SkyDescription with session summary
        """
        style = style or self.default_style
        parts = []

        # Session duration
        if state.session_start:
            duration = datetime.now() - state.session_start
            hours = duration.total_seconds() / 3600

            if hours < 1:
                duration_str = f"{int(duration.total_seconds() / 60)} minutes"
            else:
                duration_str = f"{hours:.1f} hours"

            parts.append(f"This session has been running for {duration_str}.")

        # Accomplishments
        if state.targets_observed > 0:
            if state.targets_observed == 1:
                parts.append("You've observed one target.")
            else:
                parts.append(f"You've observed {state.targets_observed} targets.")

        if state.frames_captured > 0:
            parts.append(f"Captured {state.frames_captured} frames.")

        # Current conditions summary
        condition_text = self._get_condition_summary(state)
        parts.append(condition_text)

        # Combine
        text = " ".join(parts)

        return SkyDescription(
            text=text,
            style=style,
            objects_mentioned=[],
        )

    def suggest_targets(
        self,
        state: SkyState,
        style: Optional[DescriptionStyle] = None,
        max_suggestions: int = 3,
    ) -> SkyDescription:
        """
        Generate target suggestions based on current sky.

        Args:
            state: Current sky state
            style: Description style
            max_suggestions: Maximum targets to suggest

        Returns:
            SkyDescription with suggestions
        """
        style = style or self.default_style

        if not state.visible_objects:
            return SkyDescription(
                text="I don't have visibility information for objects right now.",
                style=style,
                objects_mentioned=[],
            )

        # Score objects by observability
        scored = []
        for obj in state.visible_objects:
            score = self._calculate_observability_score(obj, state)
            scored.append((obj, score))

        # Sort by score and take top suggestions
        scored.sort(key=lambda x: x[1], reverse=True)
        top_objects = [obj for obj, _ in scored[:max_suggestions]]

        # Generate suggestion text
        if len(top_objects) == 1:
            obj = top_objects[0]
            text = f"I'd recommend {obj.name} in {obj.constellation}. "
            text += random.choice(VISIBILITY_PHRASES["good"]).capitalize() + "."
        else:
            names = [obj.name for obj in top_objects]
            if len(names) == 2:
                text = f"Good targets right now include {names[0]} and {names[1]}."
            else:
                text = f"Good targets right now include {', '.join(names[:-1])}, and {names[-1]}."

            # Add detail about best one
            best = top_objects[0]
            text += f" {best.name} is particularly well placed."

        return SkyDescription(
            text=text,
            style=style,
            objects_mentioned=[obj.name for obj in top_objects],
        )

    def _describe_conditions(
        self,
        state: SkyState,
        style: DescriptionStyle,
    ) -> str:
        """Generate conditions description."""
        intro = random.choice(CONDITION_INTROS[state.condition])

        if style == DescriptionStyle.BRIEF:
            return intro

        details = []

        if state.cloud_cover_percent > 0:
            if state.cloud_cover_percent < 25:
                details.append("with only scattered clouds")
            elif state.cloud_cover_percent < 50:
                details.append("with some clouds present")
            elif state.cloud_cover_percent < 75:
                details.append("with significant cloud cover")
            else:
                details.append("with heavy cloud cover")

        if state.seeing_arcsec is not None and style == DescriptionStyle.DETAILED:
            if state.seeing_arcsec < 2.0:
                details.append("excellent seeing")
            elif state.seeing_arcsec < 3.0:
                details.append("good seeing")
            elif state.seeing_arcsec < 4.0:
                details.append("average seeing")
            else:
                details.append("poor seeing")

        if details:
            return f"{intro} {', '.join(details).capitalize()}."
        return intro

    def _describe_moon(self, state: SkyState, style: DescriptionStyle) -> str:
        """Generate moon description."""
        phase_text = MOON_PHRASES.get(
            state.moon_phase,
            f"The moon is in {state.moon_phase} phase."
        )

        if style == DescriptionStyle.BRIEF:
            if state.moon_illumination > 0.5:
                return "The bright moon affects deep sky viewing."
            return ""

        return phase_text

    def _describe_objects(
        self,
        objects: list[VisibleObject],
        style: DescriptionStyle,
        max_objects: int,
    ) -> tuple[list[str], list[str]]:
        """Generate object descriptions."""
        descriptions = []
        mentioned = []

        # Sort by altitude (highest first) for importance
        sorted_objects = sorted(
            objects,
            key=lambda o: o.altitude_deg,
            reverse=True,
        )

        for obj in sorted_objects[:max_objects]:
            desc = self.describe_object(obj, style=style)
            descriptions.append(desc.text)
            mentioned.append(obj.name)

        return descriptions, mentioned

    def _combine_parts(
        self,
        parts: list[str],
        style: DescriptionStyle,
    ) -> str:
        """Combine description parts into flowing text."""
        if not parts:
            return ""

        if style == DescriptionStyle.BRIEF:
            return " ".join(parts)

        # Add some variety in connectors
        connectors = [" ", " Meanwhile, ", " Additionally, ", " "]

        result = parts[0]
        for i, part in enumerate(parts[1:], 1):
            connector = connectors[i % len(connectors)]
            result += connector + part

        return result

    def _assess_visibility(self, obj: VisibleObject) -> str:
        """Assess visibility quality for an object."""
        if obj.is_transiting:
            return "transiting"
        if obj.is_rising:
            return "rising"
        if obj.is_setting:
            return "setting"

        if obj.altitude_deg >= 60:
            return "excellent"
        elif obj.altitude_deg >= 40:
            return "good"
        elif obj.altitude_deg >= 20:
            return "fair"
        else:
            return "poor"

    def _assess_brightness(self, obj: VisibleObject) -> str:
        """Assess brightness category for an object."""
        if obj.magnitude is None:
            return "telescope"

        if obj.magnitude <= 4.0:
            return "naked_eye"
        elif obj.magnitude <= 7.0:
            return "binocular"
        elif obj.magnitude <= 10.0:
            return "telescope"
        else:
            return "faint"

    def _azimuth_to_direction(self, azimuth: float) -> str:
        """Convert azimuth to cardinal direction."""
        directions = [
            "north", "northeast", "east", "southeast",
            "south", "southwest", "west", "northwest", "north"
        ]
        index = int((azimuth + 22.5) / 45) % 8
        return directions[index]

    def _get_detailed_info(
        self,
        obj: VisibleObject,
        state: Optional[SkyState],
    ) -> str:
        """Get detailed technical information."""
        parts = []

        if obj.magnitude is not None:
            parts.append(f"Magnitude {obj.magnitude:.1f}")

        parts.append(f"Alt/Az: {obj.altitude_deg:.0f}°/{obj.azimuth_deg:.0f}°")

        if obj.moon_separation_deg is not None:
            parts.append(f"{obj.moon_separation_deg:.0f}° from Moon")

        if parts:
            return "(" + ", ".join(parts) + ")"
        return ""

    def _add_poetic_flourish(self, text: str, obj: VisibleObject) -> str:
        """Add poetic language for evocative descriptions."""
        flourishes = {
            "galaxy": [
                " — a distant island universe beckoning across the void.",
                ", its spiral arms forever frozen in cosmic dance.",
                ", light that left when dinosaurs roamed Earth.",
            ],
            "nebula": [
                " — stellar nursery birthing new suns.",
                ", where stars are born in clouds of fire.",
                ", painting the cosmos in ethereal hues.",
            ],
            "cluster": [
                " — diamonds scattered on velvet darkness.",
                ", a family of stars bound by ancient gravity.",
                ", jewels of the celestial sphere.",
            ],
            "planet": [
                " — wanderer among the fixed stars.",
                ", following its eternal orbital path.",
                ", our neighbor in the cosmic dance.",
            ],
        }

        object_flourishes = flourishes.get(obj.object_type.lower(), [])
        if object_flourishes:
            # Remove trailing period if present
            if text.endswith("."):
                text = text[:-1]
            text += random.choice(object_flourishes)

        return text

    def _get_condition_summary(self, state: SkyState) -> str:
        """Get brief condition summary."""
        if state.condition == SkyCondition.EXCELLENT:
            return "Conditions remain excellent."
        elif state.condition == SkyCondition.GOOD:
            return "Conditions are holding steady."
        elif state.condition == SkyCondition.FAIR:
            return "Conditions are adequate."
        elif state.condition == SkyCondition.POOR:
            return "Conditions have been challenging."
        else:
            return "Conditions are difficult."

    def _calculate_observability_score(
        self,
        obj: VisibleObject,
        state: SkyState,
    ) -> float:
        """Calculate observability score for an object."""
        score = 0.0

        # Altitude score (0-40 points)
        if obj.altitude_deg >= 60:
            score += 40
        elif obj.altitude_deg >= 40:
            score += 30
        elif obj.altitude_deg >= 20:
            score += 15
        else:
            score += 5

        # Transit bonus
        if obj.is_transiting:
            score += 20

        # Rising objects get slight bonus (will be visible longer)
        if obj.is_rising:
            score += 10

        # Moon separation bonus
        if obj.moon_separation_deg is not None:
            if obj.moon_separation_deg > 90:
                score += 15
            elif obj.moon_separation_deg > 60:
                score += 10
            elif obj.moon_separation_deg > 30:
                score += 5

        # Brightness accessibility
        if obj.magnitude is not None:
            if obj.magnitude <= 6:
                score += 15
            elif obj.magnitude <= 9:
                score += 10
            else:
                score += 5

        return score


# =============================================================================
# Module-level singleton
# =============================================================================

_describer: Optional[SkyDescriber] = None


def get_sky_describer() -> SkyDescriber:
    """Get the global sky describer instance."""
    global _describer
    if _describer is None:
        _describer = SkyDescriber()
    return _describer
