"""
NIGHTWATCH Sky Describer Tests

Tests for natural sky description generation (Step 137).
"""

import pytest
from datetime import datetime, timedelta

from services.nlp.sky_describer import (
    SkyDescriber,
    DescriptionStyle,
    SkyCondition,
    VisibleObject,
    SkyState,
    SkyDescription,
    get_sky_describer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def describer():
    """Create a SkyDescriber."""
    return SkyDescriber()


@pytest.fixture
def sample_object():
    """Create a sample visible object."""
    return VisibleObject(
        name="M31",
        object_type="galaxy",
        constellation="Andromeda",
        altitude_deg=55.0,
        azimuth_deg=45.0,
        magnitude=3.4,
    )


@pytest.fixture
def sample_objects():
    """Create a list of sample visible objects."""
    return [
        VisibleObject(
            name="M31",
            object_type="galaxy",
            constellation="Andromeda",
            altitude_deg=65.0,
            azimuth_deg=45.0,
            magnitude=3.4,
        ),
        VisibleObject(
            name="M42",
            object_type="nebula",
            constellation="Orion",
            altitude_deg=45.0,
            azimuth_deg=180.0,
            magnitude=4.0,
            is_transiting=True,
        ),
        VisibleObject(
            name="Jupiter",
            object_type="planet",
            constellation="Taurus",
            altitude_deg=35.0,
            azimuth_deg=120.0,
            magnitude=-2.5,
        ),
        VisibleObject(
            name="M45",
            object_type="cluster",
            constellation="Taurus",
            altitude_deg=50.0,
            azimuth_deg=110.0,
            magnitude=1.6,
        ),
    ]


@pytest.fixture
def sample_state(sample_objects):
    """Create a sample sky state."""
    return SkyState(
        condition=SkyCondition.GOOD,
        cloud_cover_percent=10.0,
        transparency=0.9,
        seeing_arcsec=2.5,
        moon_phase="first_quarter",
        moon_illumination=0.5,
        visible_objects=sample_objects,
        session_start=datetime.now() - timedelta(hours=2),
        targets_observed=3,
        frames_captured=45,
    )


# =============================================================================
# VisibleObject Tests
# =============================================================================


class TestVisibleObject:
    """Tests for VisibleObject dataclass."""

    def test_object_creation(self, sample_object):
        """Create a basic visible object."""
        assert sample_object.name == "M31"
        assert sample_object.object_type == "galaxy"
        assert sample_object.constellation == "Andromeda"
        assert sample_object.altitude_deg == 55.0

    def test_object_with_status(self):
        """Create object with transit/rising/setting status."""
        obj = VisibleObject(
            name="M42",
            object_type="nebula",
            constellation="Orion",
            altitude_deg=70.0,
            azimuth_deg=180.0,
            is_transiting=True,
        )
        assert obj.is_transiting is True
        assert obj.is_rising is False

    def test_object_with_moon_separation(self):
        """Create object with moon separation."""
        obj = VisibleObject(
            name="M31",
            object_type="galaxy",
            constellation="Andromeda",
            altitude_deg=55.0,
            azimuth_deg=45.0,
            moon_separation_deg=90.0,
        )
        assert obj.moon_separation_deg == 90.0


# =============================================================================
# SkyState Tests
# =============================================================================


class TestSkyState:
    """Tests for SkyState dataclass."""

    def test_state_creation(self):
        """Create a basic sky state."""
        state = SkyState()
        assert state.condition == SkyCondition.GOOD
        assert state.cloud_cover_percent == 0.0

    def test_state_with_conditions(self, sample_state):
        """Create state with full conditions."""
        assert sample_state.condition == SkyCondition.GOOD
        assert sample_state.cloud_cover_percent == 10.0
        assert sample_state.seeing_arcsec == 2.5

    def test_state_with_session(self, sample_state):
        """State tracks session information."""
        assert sample_state.targets_observed == 3
        assert sample_state.frames_captured == 45
        assert sample_state.session_start is not None


# =============================================================================
# SkyDescription Tests
# =============================================================================


class TestSkyDescription:
    """Tests for SkyDescription dataclass."""

    def test_description_creation(self):
        """Create a basic description."""
        desc = SkyDescription(
            text="The sky is clear tonight.",
            style=DescriptionStyle.CONVERSATIONAL,
        )
        assert desc.text == "The sky is clear tonight."
        assert desc.style == DescriptionStyle.CONVERSATIONAL

    def test_description_to_dict(self):
        """Description converts to dict."""
        desc = SkyDescription(
            text="Test description",
            style=DescriptionStyle.BRIEF,
            objects_mentioned=["M31", "M42"],
        )
        d = desc.to_dict()
        assert d["text"] == "Test description"
        assert d["style"] == "brief"
        assert "M31" in d["objects_mentioned"]


# =============================================================================
# Basic Description Tests
# =============================================================================


class TestBasicDescriptions:
    """Tests for basic description generation."""

    def test_describe_sky(self, describer, sample_state):
        """Generate complete sky description."""
        desc = describer.describe_sky(sample_state)

        assert desc.text is not None
        assert len(desc.text) > 0
        assert desc.style == DescriptionStyle.CONVERSATIONAL

    def test_describe_sky_brief(self, describer, sample_state):
        """Generate brief sky description."""
        desc = describer.describe_sky(sample_state, style=DescriptionStyle.BRIEF)

        assert desc.style == DescriptionStyle.BRIEF
        # Brief should be shorter
        detailed = describer.describe_sky(sample_state, style=DescriptionStyle.DETAILED)
        assert len(desc.text) <= len(detailed.text)

    def test_describe_sky_mentions_objects(self, describer, sample_state):
        """Sky description mentions visible objects."""
        desc = describer.describe_sky(sample_state, include_objects=True)

        assert len(desc.objects_mentioned) > 0

    def test_describe_sky_without_objects(self, describer, sample_state):
        """Sky description can exclude objects."""
        desc = describer.describe_sky(sample_state, include_objects=False)

        assert len(desc.objects_mentioned) == 0


# =============================================================================
# Object Description Tests
# =============================================================================


class TestObjectDescriptions:
    """Tests for object-specific descriptions."""

    def test_describe_galaxy(self, describer):
        """Describe a galaxy."""
        obj = VisibleObject(
            name="M31",
            object_type="galaxy",
            constellation="Andromeda",
            altitude_deg=55.0,
            azimuth_deg=45.0,
        )
        desc = describer.describe_object(obj)

        assert "M31" in desc.text
        assert "Andromeda" in desc.text

    def test_describe_nebula(self, describer):
        """Describe a nebula."""
        obj = VisibleObject(
            name="M42",
            object_type="nebula",
            constellation="Orion",
            altitude_deg=45.0,
            azimuth_deg=180.0,
        )
        desc = describer.describe_object(obj)

        assert "M42" in desc.text
        assert "Orion" in desc.text

    def test_describe_planet(self, describer):
        """Describe a planet."""
        obj = VisibleObject(
            name="Jupiter",
            object_type="planet",
            constellation="Taurus",
            altitude_deg=35.0,
            azimuth_deg=120.0,
            magnitude=-2.5,
        )
        desc = describer.describe_object(obj)

        assert "Jupiter" in desc.text

    def test_describe_cluster(self, describer):
        """Describe a star cluster."""
        obj = VisibleObject(
            name="M45",
            object_type="cluster",
            constellation="Taurus",
            altitude_deg=50.0,
            azimuth_deg=110.0,
        )
        desc = describer.describe_object(obj)

        assert "M45" in desc.text

    def test_describe_transiting_object(self, describer):
        """Describe object at transit."""
        obj = VisibleObject(
            name="M42",
            object_type="nebula",
            constellation="Orion",
            altitude_deg=70.0,
            azimuth_deg=180.0,
            is_transiting=True,
        )
        desc = describer.describe_object(obj)

        # Should mention high position or transit
        assert "M42" in desc.text

    def test_describe_rising_object(self, describer):
        """Describe rising object."""
        obj = VisibleObject(
            name="M31",
            object_type="galaxy",
            constellation="Andromeda",
            altitude_deg=15.0,
            azimuth_deg=70.0,
            is_rising=True,
        )
        desc = describer.describe_object(obj)

        assert "M31" in desc.text

    def test_describe_setting_object(self, describer):
        """Describe setting object."""
        obj = VisibleObject(
            name="M13",
            object_type="cluster",
            constellation="Hercules",
            altitude_deg=20.0,
            azimuth_deg=290.0,
            is_setting=True,
        )
        desc = describer.describe_object(obj)

        assert "M13" in desc.text


# =============================================================================
# Style Tests
# =============================================================================


class TestDescriptionStyles:
    """Tests for different description styles."""

    def test_brief_style(self, describer, sample_object):
        """Brief style is concise."""
        desc = describer.describe_object(sample_object, style=DescriptionStyle.BRIEF)
        assert len(desc.text) > 0

    def test_conversational_style(self, describer, sample_object):
        """Conversational style is natural."""
        desc = describer.describe_object(sample_object, style=DescriptionStyle.CONVERSATIONAL)
        assert len(desc.text) > 0

    def test_detailed_style(self, describer, sample_object):
        """Detailed style includes technical info."""
        desc = describer.describe_object(sample_object, style=DescriptionStyle.DETAILED)

        # Should have more content than brief
        brief = describer.describe_object(sample_object, style=DescriptionStyle.BRIEF)
        assert len(desc.text) >= len(brief.text)

    def test_poetic_style(self, describer, sample_object):
        """Poetic style is evocative."""
        desc = describer.describe_object(sample_object, style=DescriptionStyle.POETIC)

        # Poetic should have more elaborate language
        assert len(desc.text) > 0


# =============================================================================
# Condition Description Tests
# =============================================================================


class TestConditionDescriptions:
    """Tests for condition-based descriptions."""

    def test_excellent_conditions(self, describer):
        """Describe excellent conditions."""
        state = SkyState(condition=SkyCondition.EXCELLENT)
        desc = describer.describe_sky(state, include_objects=False)

        # Should be positive
        assert len(desc.text) > 0

    def test_poor_conditions(self, describer):
        """Describe poor conditions."""
        state = SkyState(
            condition=SkyCondition.POOR,
            cloud_cover_percent=60.0,
        )
        desc = describer.describe_sky(state, include_objects=False)

        assert len(desc.text) > 0

    def test_cloud_cover_mentioned(self, describer):
        """Cloud cover is mentioned in description."""
        state = SkyState(
            condition=SkyCondition.FAIR,
            cloud_cover_percent=40.0,
        )
        desc = describer.describe_sky(state, style=DescriptionStyle.DETAILED, include_objects=False)

        # Should mention clouds
        assert "cloud" in desc.text.lower()

    def test_moon_mentioned(self, describer):
        """Moon is mentioned when bright."""
        state = SkyState(
            condition=SkyCondition.GOOD,
            moon_phase="full",
            moon_illumination=1.0,
        )
        desc = describer.describe_sky(state, include_objects=False)

        assert "moon" in desc.text.lower()


# =============================================================================
# Session Description Tests
# =============================================================================


class TestSessionDescriptions:
    """Tests for session summary descriptions."""

    def test_describe_session(self, describer, sample_state):
        """Generate session summary."""
        desc = describer.describe_session(sample_state)

        assert len(desc.text) > 0

    def test_session_mentions_duration(self, describer, sample_state):
        """Session summary mentions duration."""
        desc = describer.describe_session(sample_state)

        # Should mention time/hours/minutes
        text_lower = desc.text.lower()
        assert "hour" in text_lower or "minute" in text_lower or "running" in text_lower

    def test_session_mentions_targets(self, describer, sample_state):
        """Session summary mentions observed targets."""
        desc = describer.describe_session(sample_state)

        # Should mention targets
        assert "target" in desc.text.lower() or "observed" in desc.text.lower()

    def test_session_mentions_frames(self, describer, sample_state):
        """Session summary mentions captured frames."""
        desc = describer.describe_session(sample_state)

        assert "frame" in desc.text.lower() or "captured" in desc.text.lower()


# =============================================================================
# Suggestion Tests
# =============================================================================


class TestSuggestions:
    """Tests for target suggestion generation."""

    def test_suggest_targets(self, describer, sample_state):
        """Generate target suggestions."""
        desc = describer.suggest_targets(sample_state)

        assert len(desc.text) > 0
        assert len(desc.objects_mentioned) > 0

    def test_suggest_targets_limits(self, describer, sample_state):
        """Suggestion respects max limit."""
        desc = describer.suggest_targets(sample_state, max_suggestions=2)

        assert len(desc.objects_mentioned) <= 2

    def test_suggest_targets_empty(self, describer):
        """Handle empty object list."""
        state = SkyState(visible_objects=[])
        desc = describer.suggest_targets(state)

        assert len(desc.text) > 0
        assert len(desc.objects_mentioned) == 0

    def test_suggestions_favor_high_altitude(self, describer, sample_objects):
        """Suggestions favor high-altitude objects."""
        state = SkyState(visible_objects=sample_objects)
        desc = describer.suggest_targets(state, max_suggestions=1)

        # M31 has highest altitude (65°)
        assert "M31" in desc.objects_mentioned or "M42" in desc.objects_mentioned


# =============================================================================
# Utility Tests
# =============================================================================


class TestUtilities:
    """Tests for utility functions."""

    def test_azimuth_to_direction(self, describer):
        """Convert azimuth to cardinal direction."""
        assert describer._azimuth_to_direction(0) == "north"
        assert describer._azimuth_to_direction(90) == "east"
        assert describer._azimuth_to_direction(180) == "south"
        assert describer._azimuth_to_direction(270) == "west"

    def test_assess_visibility_excellent(self, describer):
        """High altitude objects have excellent visibility."""
        obj = VisibleObject(
            name="Test",
            object_type="galaxy",
            constellation="Test",
            altitude_deg=70.0,
            azimuth_deg=0.0,
        )
        assert describer._assess_visibility(obj) == "excellent"

    def test_assess_visibility_poor(self, describer):
        """Low altitude objects have poor visibility."""
        obj = VisibleObject(
            name="Test",
            object_type="galaxy",
            constellation="Test",
            altitude_deg=15.0,
            azimuth_deg=0.0,
        )
        assert describer._assess_visibility(obj) == "poor"

    def test_assess_brightness_naked_eye(self, describer):
        """Bright objects are naked eye visible."""
        obj = VisibleObject(
            name="Test",
            object_type="planet",
            constellation="Test",
            altitude_deg=45.0,
            azimuth_deg=0.0,
            magnitude=-2.0,
        )
        assert describer._assess_brightness(obj) == "naked_eye"

    def test_assess_brightness_telescope(self, describer):
        """Dim objects require telescope."""
        obj = VisibleObject(
            name="Test",
            object_type="galaxy",
            constellation="Test",
            altitude_deg=45.0,
            azimuth_deg=0.0,
            magnitude=9.0,
        )
        assert describer._assess_brightness(obj) == "telescope"


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_description_styles(self):
        """All description styles defined."""
        assert DescriptionStyle.BRIEF.value == "brief"
        assert DescriptionStyle.CONVERSATIONAL.value == "conversational"
        assert DescriptionStyle.DETAILED.value == "detailed"
        assert DescriptionStyle.POETIC.value == "poetic"

    def test_sky_conditions(self):
        """All sky conditions defined."""
        assert SkyCondition.EXCELLENT.value == "excellent"
        assert SkyCondition.GOOD.value == "good"
        assert SkyCondition.FAIR.value == "fair"
        assert SkyCondition.POOR.value == "poor"
        assert SkyCondition.UNUSABLE.value == "unusable"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_sky_describer_returns_singleton(self):
        """get_sky_describer returns same instance."""
        d1 = get_sky_describer()
        d2 = get_sky_describer()
        assert d1 is d2

    def test_get_sky_describer_creates_instance(self):
        """get_sky_describer creates instance."""
        describer = get_sky_describer()
        assert isinstance(describer, SkyDescriber)
