"""
NIGHTWATCH Conversation Context Tests

Tests for multi-turn conversation context tracking (Step 128).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from services.nlp.conversation_context import (
    ConversationContext,
    EntityType,
    TrackedEntity,
    ContextMessage,
    UserIntent,
    get_context_manager,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context():
    """Create a fresh ConversationContext."""
    return ConversationContext()


@pytest.fixture
def context_with_history(context):
    """Create context with some conversation history."""
    context.add_user_message("Point the telescope at M31")
    context.track_entity("M31", EntityType.CELESTIAL_OBJECT, {"type": "galaxy"})
    context.add_assistant_message(
        "Slewing to M31, the Andromeda Galaxy.",
        tool_calls=["slew_to_target"],
    )
    context.add_user_message("What's the weather like?")
    context.add_assistant_message("Current conditions are good for observing.")
    return context


# =============================================================================
# Entity Type Tests
# =============================================================================


class TestEntityType:
    """Tests for EntityType enum."""

    def test_all_entity_types_exist(self):
        """All expected entity types are defined."""
        assert EntityType.CELESTIAL_OBJECT.value == "celestial_object"
        assert EntityType.EQUIPMENT.value == "equipment"
        assert EntityType.LOCATION.value == "location"
        assert EntityType.CONDITION.value == "condition"
        assert EntityType.TIME.value == "time"
        assert EntityType.SETTING.value == "setting"
        assert EntityType.ACTION.value == "action"


class TestUserIntent:
    """Tests for UserIntent enum."""

    def test_all_intent_types_exist(self):
        """All expected intent types are defined."""
        assert UserIntent.OBSERVE.value == "observe"
        assert UserIntent.CAPTURE.value == "capture"
        assert UserIntent.STATUS.value == "status"
        assert UserIntent.CONTROL.value == "control"
        assert UserIntent.QUERY.value == "query"
        assert UserIntent.CONFIGURE.value == "configure"
        assert UserIntent.UNKNOWN.value == "unknown"


# =============================================================================
# Tracked Entity Tests
# =============================================================================


class TestTrackedEntity:
    """Tests for TrackedEntity dataclass."""

    def test_entity_creation(self):
        """Create a basic tracked entity."""
        entity = TrackedEntity(
            name="M31",
            entity_type=EntityType.CELESTIAL_OBJECT,
        )
        assert entity.name == "M31"
        assert entity.entity_type == EntityType.CELESTIAL_OBJECT
        assert entity.mention_count == 1

    def test_entity_touch_updates(self):
        """Touch updates last_referenced and count."""
        entity = TrackedEntity(
            name="M31",
            entity_type=EntityType.CELESTIAL_OBJECT,
        )
        original_time = entity.last_referenced
        entity.touch()
        assert entity.mention_count == 2
        assert entity.last_referenced >= original_time

    def test_entity_aliases(self):
        """Entity can have aliases."""
        entity = TrackedEntity(
            name="M31",
            entity_type=EntityType.CELESTIAL_OBJECT,
        )
        entity.add_alias("Andromeda")
        entity.add_alias("NGC 224")

        assert entity.matches("M31")
        assert entity.matches("andromeda")
        assert entity.matches("NGC 224")
        assert not entity.matches("M42")

    def test_recency_score_decays(self):
        """Recency score decays over time."""
        entity = TrackedEntity(
            name="M31",
            entity_type=EntityType.CELESTIAL_OBJECT,
        )
        # Just created, should be very close to 1.0
        assert entity.recency_score >= 0.99

        # Simulate old entity
        entity.last_referenced = datetime.now() - timedelta(minutes=15)
        assert entity.recency_score < 0.2

    def test_importance_score(self):
        """Importance combines recency and frequency."""
        entity = TrackedEntity(
            name="M31",
            entity_type=EntityType.CELESTIAL_OBJECT,
        )
        # New entity with 1 mention
        initial_score = entity.importance_score

        # Touch multiple times
        for _ in range(4):
            entity.touch()

        # Should have higher importance
        assert entity.importance_score >= initial_score


# =============================================================================
# Context Message Tests
# =============================================================================


class TestContextMessage:
    """Tests for ContextMessage dataclass."""

    def test_message_creation(self):
        """Create a basic context message."""
        msg = ContextMessage(
            role="user",
            content="Point at M31",
        )
        assert msg.role == "user"
        assert msg.content == "Point at M31"

    def test_message_to_dict(self):
        """Message converts to dict for API."""
        msg = ContextMessage(
            role="user",
            content="Point at M31",
            intent=UserIntent.OBSERVE,
        )
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "Point at M31"

    def test_message_age(self):
        """Message age calculation."""
        msg = ContextMessage(role="user", content="test")
        assert msg.age_seconds < 1.0


# =============================================================================
# Message Management Tests
# =============================================================================


class TestMessageManagement:
    """Tests for message management."""

    def test_add_user_message(self, context):
        """Add a user message to context."""
        msg = context.add_user_message("Point at M31")
        assert msg.role == "user"
        assert msg.content == "Point at M31"
        assert msg.intent == UserIntent.OBSERVE

    def test_add_assistant_message(self, context):
        """Add an assistant message."""
        msg = context.add_assistant_message(
            "Slewing to M31",
            tool_calls=["slew_to_target"],
        )
        assert msg.role == "assistant"
        assert "slew_to_target" in msg.tool_calls

    def test_add_system_message(self, context):
        """Add a system message."""
        msg = context.add_system_message("Tool result: success")
        assert msg.role == "system"

    def test_message_history_maintained(self, context_with_history):
        """Message history is maintained."""
        messages = context_with_history.get_context_messages(max_messages=10)
        # Should have entity summary + messages
        assert len(messages) >= 4


# =============================================================================
# Entity Tracking Tests
# =============================================================================


class TestEntityTracking:
    """Tests for entity tracking."""

    def test_track_celestial_object(self, context):
        """Track a celestial object."""
        entity = context.track_entity(
            "M31",
            EntityType.CELESTIAL_OBJECT,
            attributes={"type": "galaxy", "magnitude": 3.4},
        )
        assert entity.name == "M31"
        assert entity.attributes["type"] == "galaxy"

    def test_track_updates_existing(self, context):
        """Tracking same entity updates it."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        entity = context.track_entity(
            "M31",
            EntityType.CELESTIAL_OBJECT,
            attributes={"distance": "2.5 Mly"},
        )
        assert entity.mention_count == 2
        assert entity.attributes["distance"] == "2.5 Mly"

    def test_get_entity_by_name(self, context):
        """Get entity by name."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        entity = context.get_entity("M31")
        assert entity is not None
        assert entity.name == "M31"

    def test_get_entity_by_alias(self, context):
        """Get entity by alias."""
        context.track_entity(
            "M31",
            EntityType.CELESTIAL_OBJECT,
            aliases=["Andromeda", "NGC 224"],
        )
        entity = context.get_entity("Andromeda")
        assert entity is not None
        assert entity.name == "M31"

    def test_get_entity_not_found(self, context):
        """Get entity returns None for unknown."""
        entity = context.get_entity("Unknown")
        assert entity is None

    def test_get_recent_entities(self, context):
        """Get recently mentioned entities."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        context.track_entity("M42", EntityType.CELESTIAL_OBJECT)
        context.track_entity("M45", EntityType.CELESTIAL_OBJECT)

        recent = context.get_recent_entities(EntityType.CELESTIAL_OBJECT)
        assert len(recent) == 3
        # Most recent should be first (highest importance)
        assert recent[0].name == "M45"

    def test_get_recent_filters_by_type(self, context):
        """Get recent entities filters by type."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        context.track_entity("cloudy", EntityType.CONDITION)

        objects = context.get_recent_entities(EntityType.CELESTIAL_OBJECT)
        assert len(objects) == 1
        assert objects[0].name == "M31"

    def test_get_last_entity(self, context):
        """Get the most recent entity."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        context.track_entity("M42", EntityType.CELESTIAL_OBJECT)

        last = context.get_last_entity(EntityType.CELESTIAL_OBJECT)
        assert last is not None
        assert last.name == "M42"


# =============================================================================
# Intent Classification Tests
# =============================================================================


class TestIntentClassification:
    """Tests for intent classification."""

    def test_classify_observe_intent(self, context):
        """Observe intent is classified."""
        msg = context.add_user_message("Point the telescope at M31")
        assert msg.intent == UserIntent.OBSERVE

    def test_classify_slew_intent(self, context):
        """Slew command is observe intent."""
        msg = context.add_user_message("Slew to NGC 7000")
        assert msg.intent == UserIntent.OBSERVE

    def test_classify_capture_intent(self, context):
        """Capture intent is classified."""
        msg = context.add_user_message("Take a 60 second image")
        assert msg.intent == UserIntent.CAPTURE

    def test_classify_status_intent(self, context):
        """Status intent is classified."""
        msg = context.add_user_message("What's the weather like?")
        assert msg.intent == UserIntent.STATUS

    def test_classify_control_intent(self, context):
        """Control intent is classified."""
        msg = context.add_user_message("Park the telescope")
        assert msg.intent == UserIntent.CONTROL

    def test_classify_query_intent(self, context):
        """Query intent is classified."""
        msg = context.add_user_message("Describe NGC 7000 for me")
        assert msg.intent == UserIntent.QUERY

    def test_classify_configure_intent(self, context):
        """Configure intent is classified."""
        msg = context.add_user_message("Change the gain to 200")
        assert msg.intent == UserIntent.CONFIGURE

    def test_classify_unknown_intent(self, context):
        """Unknown intent for unrecognized messages."""
        msg = context.add_user_message("Hello there")
        assert msg.intent == UserIntent.UNKNOWN


# =============================================================================
# Entity Extraction Tests
# =============================================================================


class TestEntityExtraction:
    """Tests for entity extraction from text."""

    def test_extract_messier_object(self, context):
        """Extract Messier objects."""
        msg = context.add_user_message("Point at M31")
        assert "M31" in msg.entities_mentioned

    def test_extract_messier_with_space(self, context):
        """Extract Messier with space (M 42)."""
        msg = context.add_user_message("Slew to M 42")
        assert "M42" in msg.entities_mentioned

    def test_extract_ngc_object(self, context):
        """Extract NGC objects."""
        msg = context.add_user_message("Let's observe NGC 7000")
        assert "NGC7000" in msg.entities_mentioned

    def test_extract_ic_object(self, context):
        """Extract IC objects."""
        msg = context.add_user_message("Show me IC 1396")
        assert "IC1396" in msg.entities_mentioned

    def test_extract_named_star(self, context):
        """Extract named stars."""
        msg = context.add_user_message("Center on Vega")
        assert "Vega" in msg.entities_mentioned

    def test_extract_planet(self, context):
        """Extract planet names."""
        msg = context.add_user_message("Point at Jupiter")
        assert "Jupiter" in msg.entities_mentioned

    def test_extract_multiple_objects(self, context):
        """Extract multiple objects from one message."""
        msg = context.add_user_message("Compare M31 and M33")
        assert "M31" in msg.entities_mentioned
        assert "M33" in msg.entities_mentioned


# =============================================================================
# Reference Resolution Tests
# =============================================================================


class TestReferenceResolution:
    """Tests for reference resolution."""

    def test_resolve_it_reference(self, context_with_history):
        """Resolve 'it' to last celestial object."""
        resolved = context_with_history.resolve_reference("it")
        assert resolved == "M31"

    def test_resolve_that_reference(self, context_with_history):
        """Resolve 'that' to last celestial object."""
        resolved = context_with_history.resolve_reference("that")
        assert resolved == "M31"

    def test_resolve_same_target(self, context_with_history):
        """Resolve 'the same target' reference."""
        resolved = context_with_history.resolve_reference("the same target")
        assert resolved == "M31"

    def test_resolve_unknown_reference(self, context):
        """Unknown reference returns None."""
        resolved = context.resolve_reference("it")
        assert resolved is None

    def test_expand_references(self, context_with_history):
        """Expand references in text."""
        text = "Take an image of it"
        expanded = context_with_history.expand_references(text)
        assert "M31" in expanded


# =============================================================================
# Context Building Tests
# =============================================================================


class TestContextBuilding:
    """Tests for context building."""

    def test_get_context_messages(self, context_with_history):
        """Get context messages for LLM."""
        messages = context_with_history.get_context_messages(max_messages=5)
        assert len(messages) >= 2
        # First should be system context
        assert messages[0]["role"] == "system"

    def test_get_context_summary(self, context_with_history):
        """Get human-readable context summary."""
        summary = context_with_history.get_context_summary()
        assert "M31" in summary
        assert len(summary) > 0

    def test_context_summary_empty(self, context):
        """Empty context returns 'No context'."""
        summary = context.get_context_summary()
        assert summary == "No context"


# =============================================================================
# User Preference Tests
# =============================================================================


class TestUserPreferences:
    """Tests for user preference learning."""

    def test_get_preferred_targets(self, context):
        """Get frequently mentioned targets."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)  # Mention twice
        context.track_entity("M42", EntityType.CELESTIAL_OBJECT)

        preferred = context.get_preferred_targets(limit=5)
        assert "M31" in preferred
        assert preferred[0] == "M31"  # Most mentioned first

    def test_get_intent_trend(self, context):
        """Get dominant recent intent."""
        context.add_user_message("Point at M31")
        context.add_user_message("Slew to M42")
        context.add_user_message("Go to M45")

        trend = context.get_intent_trend()
        assert trend == UserIntent.OBSERVE

    def test_intent_trend_none_when_empty(self, context):
        """No trend when no history."""
        trend = context.get_intent_trend()
        assert trend is None


# =============================================================================
# Context Pruning Tests
# =============================================================================


class TestContextPruning:
    """Tests for context pruning."""

    def test_messages_pruned_by_count(self, context):
        """Old messages are pruned by count."""
        # Add more than MAX_MESSAGES
        for i in range(60):
            context.add_user_message(f"Message {i}")

        messages = context.get_context_messages(max_messages=100)
        # Should be pruned to MAX_MESSAGES
        assert len(messages) <= context.MAX_MESSAGES + 1  # +1 for entity summary

    def test_clear_context(self, context_with_history):
        """Clear all context."""
        context_with_history.clear()
        assert context_with_history.get_context_summary() == "No context"


# =============================================================================
# Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for context serialization."""

    def test_to_dict(self, context_with_history):
        """Context can be serialized to dict."""
        d = context_with_history.to_dict()
        assert "message_count" in d
        assert "entity_count" in d
        assert "entities" in d
        assert d["entity_count"] >= 1

    def test_to_dict_includes_entities(self, context):
        """Serialized dict includes entity info."""
        context.track_entity("M31", EntityType.CELESTIAL_OBJECT)
        d = context.to_dict()
        assert "m31" in d["entities"]
        assert d["entities"]["m31"]["type"] == "celestial_object"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_context_manager_returns_singleton(self):
        """get_context_manager returns same instance."""
        ctx1 = get_context_manager()
        ctx2 = get_context_manager()
        assert ctx1 is ctx2

    def test_get_context_manager_creates_instance(self):
        """get_context_manager creates instance if needed."""
        ctx = get_context_manager()
        assert isinstance(ctx, ConversationContext)
