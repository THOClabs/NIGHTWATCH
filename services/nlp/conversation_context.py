"""
NIGHTWATCH Conversation Context Manager (Step 128)

Provides multi-turn conversation context tracking for natural language
understanding. Tracks mentioned entities, resolves references, and maintains
context windows for coherent multi-turn interactions.

Features:
- Entity tracking (celestial objects, weather conditions, equipment states)
- Reference resolution ("it", "that", "the same target")
- Context windowing with relevance-based pruning
- User intent history for proactive suggestions

Usage:
    from nightwatch.conversation_context import ConversationContext

    context = ConversationContext()
    context.add_user_message("Point at M31")
    context.track_entity("M31", EntityType.CELESTIAL_OBJECT, {"type": "galaxy"})

    # Later, resolve reference
    resolved = context.resolve_reference("it")  # Returns "M31"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("NIGHTWATCH.ConversationContext")


__all__ = [
    "ConversationContext",
    "EntityType",
    "TrackedEntity",
    "ContextMessage",
    "UserIntent",
    "get_context_manager",
]


# =============================================================================
# Enums and Data Classes
# =============================================================================


class EntityType(Enum):
    """Types of entities tracked in conversation context."""
    CELESTIAL_OBJECT = "celestial_object"  # M31, NGC 7000, Vega, etc.
    EQUIPMENT = "equipment"                 # telescope, camera, guider
    LOCATION = "location"                   # coordinates, constellation
    CONDITION = "condition"                 # weather, seeing, humidity
    TIME = "time"                          # observation time, duration
    SETTING = "setting"                    # exposure, gain, binning
    ACTION = "action"                      # slew, park, capture


class UserIntent(Enum):
    """Classified user intents for tracking patterns."""
    OBSERVE = "observe"          # Point at, slew to, track
    CAPTURE = "capture"          # Take image, capture, photograph
    STATUS = "status"            # Check weather, status, info
    CONTROL = "control"          # Park, stop, home, calibrate
    QUERY = "query"              # What is, where is, how
    CONFIGURE = "configure"      # Set exposure, change gain
    UNKNOWN = "unknown"


@dataclass
class TrackedEntity:
    """An entity being tracked in conversation context."""
    name: str
    entity_type: EntityType
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_mentioned: datetime = field(default_factory=datetime.now)
    last_referenced: datetime = field(default_factory=datetime.now)
    mention_count: int = 1
    aliases: Set[str] = field(default_factory=set)

    def touch(self):
        """Update last referenced time and increment count."""
        self.last_referenced = datetime.now()
        self.mention_count += 1

    def add_alias(self, alias: str):
        """Add an alternative name for this entity."""
        self.aliases.add(alias.lower())

    def matches(self, name: str) -> bool:
        """Check if name matches this entity or its aliases."""
        name_lower = name.lower()
        return (
            name_lower == self.name.lower() or
            name_lower in self.aliases
        )

    @property
    def recency_score(self) -> float:
        """Score based on how recently entity was referenced (0-1)."""
        age = (datetime.now() - self.last_referenced).total_seconds()
        # Decay over 10 minutes
        return max(0.0, 1.0 - age / 600)

    @property
    def importance_score(self) -> float:
        """Combined score of recency and mention frequency."""
        frequency = min(1.0, self.mention_count / 5)
        return 0.6 * self.recency_score + 0.4 * frequency


@dataclass
class ContextMessage:
    """A message with context metadata."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[UserIntent] = None
    entities_mentioned: List[str] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "role": self.role,
            "content": self.content,
        }

    @property
    def age_seconds(self) -> float:
        """Age of message in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()


# =============================================================================
# Reference Resolution Patterns
# =============================================================================


# Pronouns and references that need resolution
REFERENCE_PATTERNS = {
    # Object references
    r"\b(it|that|this)\b": "last_object",
    r"\b(the same (one|target|object))\b": "last_object",
    r"\b(that (galaxy|nebula|cluster|star|planet))\b": "last_typed_object",
    r"\b(there|that location|those coordinates)\b": "last_location",

    # Action references
    r"\b(again|once more|repeat)\b": "last_action",
    r"\b(the same (thing|action))\b": "last_action",

    # Time references
    r"\b(then|after that|afterwards)\b": "sequence",
}

# Patterns for extracting celestial objects
CELESTIAL_PATTERNS = [
    r"\b(M\s*\d+)\b",                     # Messier objects: M31, M 42
    r"\b(NGC\s*\d+)\b",                   # NGC objects: NGC 7000
    r"\b(IC\s*\d+)\b",                    # IC objects: IC 1396
    r"\b(Sh2[-\s]*\d+)\b",                # Sharpless objects
    r"\b(HD\s*\d+)\b",                    # HD catalog stars
    r"\b(HIP\s*\d+)\b",                   # Hipparcos catalog
    # Named stars (common ones)
    r"\b(Vega|Polaris|Sirius|Betelgeuse|Rigel|Arcturus|Capella|Procyon|Altair|Deneb|Aldebaran|Antares|Spica|Regulus|Castor|Pollux)\b",
    # Planets
    r"\b(Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune)\b",
    # Named deep sky objects
    r"\b(Andromeda|Orion Nebula|Ring Nebula|Crab Nebula|Whirlpool|Pinwheel|Dumbbell|Lagoon|Trifid|Eagle Nebula)\b",
]

# Intent classification patterns
INTENT_PATTERNS = {
    UserIntent.OBSERVE: [
        r"\b(point|slew|goto|go to|track|center|aim)\b",
        r"\b(observe|look at|view|show me)\b",
    ],
    UserIntent.CAPTURE: [
        r"\b(capture|image|photograph|take|shoot|expose)\b",
        r"\b(frame|exposure|light frame)\b",
    ],
    UserIntent.STATUS: [
        r"\b(status|check|what is|how is|weather|conditions)\b",
        r"\b(tell me|show|display|report)\b",
    ],
    UserIntent.CONTROL: [
        r"\b(park|stop|halt|abort|home|emergency)\b",
        r"\b(start|begin|end|finish|close)\b",
    ],
    UserIntent.QUERY: [
        r"\b(what|where|when|why|how|which)\b",
        r"\b(tell me about|describe|explain)\b",
    ],
    UserIntent.CONFIGURE: [
        r"\b(set|change|adjust|configure|increase|decrease)\b",
        r"\b(exposure|gain|binning|filter|offset)\b",
    ],
}


# =============================================================================
# Conversation Context Manager
# =============================================================================


class ConversationContext:
    """
    Manages multi-turn conversation context for natural language understanding.

    Tracks mentioned entities, resolves references, and maintains context
    windows for coherent multi-turn interactions.
    """

    # Context window limits
    MAX_MESSAGES = 50
    MAX_ENTITIES = 100
    CONTEXT_WINDOW_MINUTES = 30

    def __init__(self):
        """Initialize conversation context manager."""
        self._messages: List[ContextMessage] = []
        self._entities: Dict[str, TrackedEntity] = {}
        self._intent_history: List[Tuple[datetime, UserIntent]] = []

        # Quick access to recent entities by type
        self._last_by_type: Dict[EntityType, str] = {}

        # Last action for "repeat" references
        self._last_action: Optional[Dict[str, Any]] = None

        logger.debug("ConversationContext initialized")

    # =========================================================================
    # Message Management
    # =========================================================================

    def add_user_message(self, content: str) -> ContextMessage:
        """
        Add a user message and extract entities/intent.

        Args:
            content: User message text

        Returns:
            ContextMessage with extracted metadata
        """
        # Classify intent
        intent = self._classify_intent(content)

        # Extract entities
        entities = self._extract_entities(content)

        # Create message
        msg = ContextMessage(
            role="user",
            content=content,
            intent=intent,
            entities_mentioned=entities,
        )

        self._messages.append(msg)
        self._intent_history.append((datetime.now(), intent))

        # Track entities
        for entity_name in entities:
            self._update_or_create_entity(entity_name, content)

        # Prune old messages
        self._prune_context()

        logger.debug(f"Added user message: intent={intent.value}, entities={entities}")
        return msg

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[str]] = None,
    ) -> ContextMessage:
        """
        Add an assistant message.

        Args:
            content: Assistant response text
            tool_calls: List of tool names called

        Returns:
            ContextMessage
        """
        msg = ContextMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls or [],
        )

        self._messages.append(msg)

        # Track last action
        if tool_calls:
            self._last_action = {
                "tools": tool_calls,
                "timestamp": datetime.now(),
                "content": content,
            }

        self._prune_context()
        return msg

    def add_system_message(self, content: str) -> ContextMessage:
        """Add a system message (tool results, etc.)."""
        msg = ContextMessage(role="system", content=content)
        self._messages.append(msg)
        return msg

    # =========================================================================
    # Entity Tracking
    # =========================================================================

    def track_entity(
        self,
        name: str,
        entity_type: EntityType,
        attributes: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None,
    ) -> TrackedEntity:
        """
        Explicitly track an entity in context.

        Args:
            name: Entity name (e.g., "M31")
            entity_type: Type of entity
            attributes: Additional attributes
            aliases: Alternative names

        Returns:
            TrackedEntity instance
        """
        key = name.lower()

        if key in self._entities:
            entity = self._entities[key]
            entity.touch()
            if attributes:
                entity.attributes.update(attributes)
        else:
            entity = TrackedEntity(
                name=name,
                entity_type=entity_type,
                attributes=attributes or {},
            )
            self._entities[key] = entity

        if aliases:
            for alias in aliases:
                entity.add_alias(alias)

        # Update last-by-type reference
        self._last_by_type[entity_type] = name

        logger.debug(f"Tracking entity: {name} ({entity_type.value})")
        return entity

    def get_entity(self, name: str) -> Optional[TrackedEntity]:
        """Get a tracked entity by name or alias."""
        key = name.lower()

        # Direct lookup
        if key in self._entities:
            return self._entities[key]

        # Alias lookup
        for entity in self._entities.values():
            if entity.matches(name):
                return entity

        return None

    def get_recent_entities(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 5,
    ) -> List[TrackedEntity]:
        """
        Get recently mentioned entities, sorted by importance.

        Args:
            entity_type: Filter by type (None = all types)
            limit: Maximum entities to return

        Returns:
            List of TrackedEntity sorted by importance
        """
        entities = list(self._entities.values())

        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        # Sort by importance score
        entities.sort(key=lambda e: e.importance_score, reverse=True)

        return entities[:limit]

    def get_last_entity(
        self,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[TrackedEntity]:
        """Get the most recently referenced entity."""
        if entity_type and entity_type in self._last_by_type:
            name = self._last_by_type[entity_type]
            return self.get_entity(name)

        # Get overall most recent
        recent = self.get_recent_entities(entity_type, limit=1)
        return recent[0] if recent else None

    # =========================================================================
    # Reference Resolution
    # =========================================================================

    def resolve_reference(self, text: str) -> Optional[str]:
        """
        Resolve a reference like "it" or "that target" to a specific entity.

        Args:
            text: Text containing reference

        Returns:
            Resolved entity name, or None if unresolvable
        """
        text_lower = text.lower()

        # Check each reference pattern
        for pattern, ref_type in REFERENCE_PATTERNS.items():
            if re.search(pattern, text_lower):
                if ref_type == "last_object":
                    entity = self.get_last_entity(EntityType.CELESTIAL_OBJECT)
                    if entity:
                        logger.debug(f"Resolved '{text}' to '{entity.name}'")
                        return entity.name

                elif ref_type == "last_typed_object":
                    # Extract object type from reference
                    entity = self.get_last_entity(EntityType.CELESTIAL_OBJECT)
                    if entity:
                        return entity.name

                elif ref_type == "last_location":
                    entity = self.get_last_entity(EntityType.LOCATION)
                    if entity:
                        return entity.name

                elif ref_type == "last_action":
                    if self._last_action:
                        return f"repeat:{self._last_action['tools'][0]}"

        return None

    def expand_references(self, text: str) -> str:
        """
        Expand all references in text to explicit entity names.

        Args:
            text: Text with potential references

        Returns:
            Text with references expanded
        """
        result = text

        # Simple pronoun replacement
        for pattern, ref_type in REFERENCE_PATTERNS.items():
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                resolved = self.resolve_reference(match.group(0))
                if resolved and not resolved.startswith("repeat:"):
                    # Replace the reference with the resolved name
                    result = result[:match.start()] + resolved + result[match.end():]

        return result

    # =========================================================================
    # Context Building
    # =========================================================================

    def get_context_messages(
        self,
        max_messages: int = 10,
        include_entities: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for context injection.

        Args:
            max_messages: Maximum messages to include
            include_entities: Whether to prepend entity summary

        Returns:
            List of message dicts for LLM API
        """
        messages = []

        # Add entity context summary if requested
        if include_entities:
            entity_summary = self._build_entity_summary()
            if entity_summary:
                messages.append({
                    "role": "system",
                    "content": f"[Context] {entity_summary}",
                })

        # Add recent messages
        recent = self._messages[-max_messages:]
        for msg in recent:
            messages.append(msg.to_dict())

        return messages

    def get_context_summary(self) -> str:
        """
        Get a text summary of current conversation context.

        Returns:
            Human-readable context summary
        """
        lines = []

        # Recent entities
        recent_objects = self.get_recent_entities(
            EntityType.CELESTIAL_OBJECT, limit=3
        )
        if recent_objects:
            names = [e.name for e in recent_objects]
            lines.append(f"Recent targets: {', '.join(names)}")

        # Last action
        if self._last_action:
            lines.append(f"Last action: {self._last_action['tools']}")

        # Intent trend
        if self._intent_history:
            recent_intents = [i[1] for i in self._intent_history[-5:]]
            intent_counts = {}
            for intent in recent_intents:
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            dominant = max(intent_counts, key=intent_counts.get)
            lines.append(f"User focus: {dominant.value}")

        return "; ".join(lines) if lines else "No context"

    # =========================================================================
    # User Preference Learning
    # =========================================================================

    def get_preferred_targets(self, limit: int = 5) -> List[str]:
        """
        Get frequently mentioned celestial objects.

        Args:
            limit: Maximum targets to return

        Returns:
            List of target names sorted by mention frequency
        """
        objects = self.get_recent_entities(EntityType.CELESTIAL_OBJECT)
        # Sort by total mention count
        objects.sort(key=lambda e: e.mention_count, reverse=True)
        return [e.name for e in objects[:limit]]

    def get_intent_trend(self) -> Optional[UserIntent]:
        """
        Analyze recent intents to determine user's current focus.

        Returns:
            Most common recent intent, or None
        """
        if not self._intent_history:
            return None

        # Look at last 10 intents
        recent = [i[1] for i in self._intent_history[-10:]]
        if not recent:
            return None

        # Count occurrences
        counts = {}
        for intent in recent:
            counts[intent] = counts.get(intent, 0) + 1

        return max(counts, key=counts.get)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _classify_intent(self, text: str) -> UserIntent:
        """Classify user intent from message text."""
        text_lower = text.lower()

        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent

        return UserIntent.UNKNOWN

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity names from text."""
        entities = []

        for pattern in CELESTIAL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)

        # Normalize (remove extra spaces)
        entities = [re.sub(r'\s+', '', e) for e in entities]

        return list(set(entities))  # Deduplicate

    def _update_or_create_entity(self, name: str, source_text: str):
        """Update existing entity or create new one."""
        key = name.lower()

        if key in self._entities:
            self._entities[key].touch()
        else:
            # Determine entity type from patterns
            entity_type = self._infer_entity_type(name)
            self.track_entity(name, entity_type)

    def _infer_entity_type(self, name: str) -> EntityType:
        """Infer entity type from its name."""
        name_upper = name.upper()

        # Check for catalog prefixes
        if any(name_upper.startswith(p) for p in ['M', 'NGC', 'IC', 'SH2', 'HD', 'HIP']):
            return EntityType.CELESTIAL_OBJECT

        # Check for planets
        planets = {'MERCURY', 'VENUS', 'MARS', 'JUPITER', 'SATURN', 'URANUS', 'NEPTUNE'}
        if name_upper in planets:
            return EntityType.CELESTIAL_OBJECT

        # Default to celestial object for now
        return EntityType.CELESTIAL_OBJECT

    def _build_entity_summary(self) -> str:
        """Build a summary string of tracked entities."""
        parts = []

        # Most recent celestial object
        obj = self.get_last_entity(EntityType.CELESTIAL_OBJECT)
        if obj:
            parts.append(f"Current target: {obj.name}")

        # Recent conditions
        cond = self.get_last_entity(EntityType.CONDITION)
        if cond:
            parts.append(f"Conditions: {cond.name}")

        return "; ".join(parts)

    def _prune_context(self):
        """Remove old messages and low-importance entities."""
        # Prune messages by count
        if len(self._messages) > self.MAX_MESSAGES:
            self._messages = self._messages[-self.MAX_MESSAGES:]

        # Prune old messages by time
        cutoff = datetime.now() - timedelta(minutes=self.CONTEXT_WINDOW_MINUTES)
        self._messages = [m for m in self._messages if m.timestamp > cutoff]

        # Prune entities by importance
        if len(self._entities) > self.MAX_ENTITIES:
            # Sort by importance and keep top entries
            sorted_entities = sorted(
                self._entities.items(),
                key=lambda x: x[1].importance_score,
                reverse=True,
            )
            self._entities = dict(sorted_entities[:self.MAX_ENTITIES])

    def clear(self):
        """Clear all conversation context."""
        self._messages.clear()
        self._entities.clear()
        self._intent_history.clear()
        self._last_by_type.clear()
        self._last_action = None
        logger.debug("Conversation context cleared")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "message_count": len(self._messages),
            "entity_count": len(self._entities),
            "entities": {
                name: {
                    "type": e.entity_type.value,
                    "mentions": e.mention_count,
                    "importance": round(e.importance_score, 2),
                }
                for name, e in self._entities.items()
            },
            "last_action": self._last_action["tools"] if self._last_action else None,
            "intent_trend": self.get_intent_trend().value if self.get_intent_trend() else None,
        }


# =============================================================================
# Module-level instance and factory
# =============================================================================


_default_context: Optional[ConversationContext] = None


def get_context_manager() -> ConversationContext:
    """
    Get or create the default conversation context manager.

    Returns:
        ConversationContext singleton instance
    """
    global _default_context
    if _default_context is None:
        _default_context = ConversationContext()
    return _default_context
