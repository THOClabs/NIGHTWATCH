"""
NIGHTWATCH Wake Word Trainer

Custom wake word training and personalization (Step 135).

This module provides:
- Custom wake word learning from user examples
- Detection success/failure tracking for adaptation
- Phonetic variation generation
- User voice pattern personalization
- Wake word model export for detector integration
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import re
from collections import Counter


# =============================================================================
# Enums and Constants
# =============================================================================


class DetectionOutcome(Enum):
    """Outcome of a wake word detection attempt."""

    TRUE_POSITIVE = "true_positive"    # Correctly detected wake word
    FALSE_POSITIVE = "false_positive"  # Detected when not spoken
    FALSE_NEGATIVE = "false_negative"  # Missed when spoken
    TRUE_NEGATIVE = "true_negative"    # Correctly ignored non-wake-word


class TrainingPhase(Enum):
    """Phase of wake word training."""

    COLLECTING = "collecting"    # Gathering examples
    TRAINING = "training"        # Processing examples
    READY = "ready"              # Model ready for use
    NEEDS_EXAMPLES = "needs_examples"  # Needs more examples


# Common phonetic substitutions for wake word variations
PHONETIC_SUBSTITUTIONS = {
    # Vowel variations
    "a": ["a", "ah", "uh"],
    "e": ["e", "eh", "ee"],
    "i": ["i", "ee", "ih"],
    "o": ["o", "oh", "aw"],
    "u": ["u", "oo", "uh"],
    # Consonant variations
    "t": ["t", "d"],
    "k": ["k", "c", "ck"],
    "s": ["s", "ss", "z"],
    "ch": ["ch", "tch", "sh"],
    "th": ["th", "t", "d"],
    # Common word-level variations
    "night": ["night", "nite", "knight"],
    "watch": ["watch", "wotch", "wach"],
}

# Common prefixes for wake phrases
WAKE_PREFIXES = [
    "",  # No prefix
    "hey ",
    "hi ",
    "ok ",
    "okay ",
    "hello ",
    "yo ",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WakeWordExample:
    """A recorded example of wake word utterance."""

    text: str  # Transcribed text
    timestamp: datetime = field(default_factory=datetime.now)
    is_positive: bool = True  # True if this is a wake word, False if not
    confidence: float = 1.0  # Confidence that this is correct
    user_confirmed: bool = False  # User explicitly confirmed

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "is_positive": self.is_positive,
            "confidence": self.confidence,
            "user_confirmed": self.user_confirmed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WakeWordExample":
        """Create from dictionary."""
        return cls(
            text=data["text"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            is_positive=data.get("is_positive", True),
            confidence=data.get("confidence", 1.0),
            user_confirmed=data.get("user_confirmed", False),
        )


@dataclass
class DetectionEvent:
    """Record of a wake word detection event."""

    text: str
    detected: bool
    outcome: DetectionOutcome
    timestamp: datetime = field(default_factory=datetime.now)
    variation_matched: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "detected": self.detected,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "variation_matched": self.variation_matched,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DetectionEvent":
        """Create from dictionary."""
        return cls(
            text=data["text"],
            detected=data["detected"],
            outcome=DetectionOutcome(data["outcome"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            variation_matched=data.get("variation_matched"),
        )


@dataclass
class WakeWordModel:
    """Trained wake word model for detection."""

    primary_phrase: str
    variations: list[str] = field(default_factory=list)
    fuzzy_threshold: float = 0.8
    trained_at: datetime = field(default_factory=datetime.now)
    example_count: int = 0
    accuracy: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "primary_phrase": self.primary_phrase,
            "variations": self.variations,
            "fuzzy_threshold": self.fuzzy_threshold,
            "trained_at": self.trained_at.isoformat(),
            "example_count": self.example_count,
            "accuracy": self.accuracy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WakeWordModel":
        """Create from dictionary."""
        return cls(
            primary_phrase=data["primary_phrase"],
            variations=data.get("variations", []),
            fuzzy_threshold=data.get("fuzzy_threshold", 0.8),
            trained_at=datetime.fromisoformat(data["trained_at"]) if data.get("trained_at") else datetime.now(),
            example_count=data.get("example_count", 0),
            accuracy=data.get("accuracy", 0.0),
        )


@dataclass
class TrainingStatus:
    """Current status of wake word training."""

    phase: TrainingPhase
    positive_examples: int
    negative_examples: int
    total_detections: int
    accuracy: float
    message: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "phase": self.phase.value,
            "positive_examples": self.positive_examples,
            "negative_examples": self.negative_examples,
            "total_detections": self.total_detections,
            "accuracy": self.accuracy,
            "message": self.message,
        }


# =============================================================================
# Wake Word Trainer
# =============================================================================


class WakeWordTrainer:
    """
    Trains and personalizes wake word detection.

    Features:
    - Collect positive and negative examples
    - Generate phonetic variations
    - Track detection accuracy
    - Adapt fuzzy matching threshold
    - Export model for detector integration
    """

    MIN_POSITIVE_EXAMPLES = 3
    MIN_NEGATIVE_EXAMPLES = 2
    OPTIMAL_EXAMPLES = 10

    def __init__(
        self,
        primary_phrase: str = "nightwatch",
        data_path: Optional[Path] = None,
        auto_save: bool = True,
    ):
        """
        Initialize wake word trainer.

        Args:
            primary_phrase: The main wake word/phrase
            data_path: Path to training data file
            auto_save: Whether to auto-save after updates
        """
        self.primary_phrase = primary_phrase.lower().strip()
        self.data_path = data_path or Path.home() / ".nightwatch" / "wake_word_training.json"
        self.auto_save = auto_save

        # Training data
        self._positive_examples: list[WakeWordExample] = []
        self._negative_examples: list[WakeWordExample] = []
        self._detection_events: list[DetectionEvent] = []

        # Current model
        self._model: Optional[WakeWordModel] = None

        # Load existing data
        self._load()

        # Generate initial variations if no model
        if self._model is None:
            self._model = self._create_initial_model()

    def _create_initial_model(self) -> WakeWordModel:
        """Create initial model with generated variations."""
        variations = self._generate_variations(self.primary_phrase)
        return WakeWordModel(
            primary_phrase=self.primary_phrase,
            variations=variations,
            fuzzy_threshold=0.8,
        )

    def _generate_variations(self, phrase: str) -> list[str]:
        """Generate phonetic and spelling variations of a phrase."""
        variations = set()
        phrase_lower = phrase.lower().strip()

        # Add base phrase
        variations.add(phrase_lower)

        # Add with different prefixes
        for prefix in WAKE_PREFIXES:
            variations.add(f"{prefix}{phrase_lower}".strip())

        # Add spacing variations
        variations.add(phrase_lower.replace(" ", ""))
        variations.add(phrase_lower.replace(" ", "-"))

        # Add word-level substitutions
        words = phrase_lower.split()
        for i, word in enumerate(words):
            for pattern, subs in PHONETIC_SUBSTITUTIONS.items():
                if pattern in word:
                    for sub in subs:
                        new_word = word.replace(pattern, sub, 1)
                        new_words = words.copy()
                        new_words[i] = new_word
                        new_phrase = " ".join(new_words)
                        variations.add(new_phrase)
                        # Also add with prefixes
                        for prefix in WAKE_PREFIXES[:3]:  # Limit prefix combinations
                            variations.add(f"{prefix}{new_phrase}".strip())

        return sorted(list(variations))

    def _load(self) -> None:
        """Load training data from disk."""
        if not self.data_path.exists():
            return

        try:
            with open(self.data_path) as f:
                data = json.load(f)

            # Load examples
            for ex_data in data.get("positive_examples", []):
                self._positive_examples.append(WakeWordExample.from_dict(ex_data))
            for ex_data in data.get("negative_examples", []):
                self._negative_examples.append(WakeWordExample.from_dict(ex_data))

            # Load events
            for ev_data in data.get("detection_events", []):
                self._detection_events.append(DetectionEvent.from_dict(ev_data))

            # Load model
            if data.get("model"):
                self._model = WakeWordModel.from_dict(data["model"])

            # Update primary phrase if stored
            if data.get("primary_phrase"):
                self.primary_phrase = data["primary_phrase"]

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        """Save training data to disk."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "primary_phrase": self.primary_phrase,
            "positive_examples": [ex.to_dict() for ex in self._positive_examples],
            "negative_examples": [ex.to_dict() for ex in self._negative_examples],
            "detection_events": [ev.to_dict() for ev in self._detection_events[-100:]],  # Keep last 100
            "model": self._model.to_dict() if self._model else None,
            "saved_at": datetime.now().isoformat(),
        }

        with open(self.data_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_positive_example(
        self,
        text: str,
        user_confirmed: bool = False,
        confidence: float = 1.0,
    ) -> None:
        """
        Add a positive example (text that IS the wake word).

        Args:
            text: The transcribed text
            user_confirmed: Whether user explicitly confirmed
            confidence: Confidence level (0-1)
        """
        example = WakeWordExample(
            text=text.lower().strip(),
            is_positive=True,
            user_confirmed=user_confirmed,
            confidence=confidence,
        )
        self._positive_examples.append(example)

        # Learn new variation if confirmed
        if user_confirmed and self._model:
            normalized = text.lower().strip()
            if normalized not in self._model.variations:
                self._model.variations.append(normalized)

        if self.auto_save:
            self._save()

    def add_negative_example(
        self,
        text: str,
        user_confirmed: bool = False,
    ) -> None:
        """
        Add a negative example (text that is NOT the wake word).

        Args:
            text: The transcribed text
            user_confirmed: Whether user explicitly confirmed
        """
        example = WakeWordExample(
            text=text.lower().strip(),
            is_positive=False,
            user_confirmed=user_confirmed,
        )
        self._negative_examples.append(example)

        if self.auto_save:
            self._save()

    def record_detection(
        self,
        text: str,
        detected: bool,
        was_correct: bool,
        variation_matched: Optional[str] = None,
    ) -> None:
        """
        Record a detection event for tracking accuracy.

        Args:
            text: The input text
            detected: Whether wake word was detected
            was_correct: Whether the detection was correct
            variation_matched: Which variation pattern matched
        """
        if detected and was_correct:
            outcome = DetectionOutcome.TRUE_POSITIVE
        elif detected and not was_correct:
            outcome = DetectionOutcome.FALSE_POSITIVE
        elif not detected and not was_correct:
            outcome = DetectionOutcome.FALSE_NEGATIVE
        else:
            outcome = DetectionOutcome.TRUE_NEGATIVE

        event = DetectionEvent(
            text=text,
            detected=detected,
            outcome=outcome,
            variation_matched=variation_matched,
        )
        self._detection_events.append(event)

        # Update model accuracy
        if self._model:
            self._model.accuracy = self._calculate_accuracy()

        if self.auto_save:
            self._save()

    def train(self) -> WakeWordModel:
        """
        Train/update the wake word model from collected examples.

        Returns:
            Updated WakeWordModel
        """
        # Start with generated variations
        variations = set(self._generate_variations(self.primary_phrase))

        # Add confirmed positive examples
        for ex in self._positive_examples:
            if ex.user_confirmed or ex.confidence >= 0.9:
                variations.add(ex.text)

        # Remove patterns that match negative examples
        for ex in self._negative_examples:
            if ex.user_confirmed:
                variations.discard(ex.text)

        # Optimize fuzzy threshold based on detection history
        threshold = self._optimize_threshold()

        # Create updated model
        self._model = WakeWordModel(
            primary_phrase=self.primary_phrase,
            variations=sorted(list(variations)),
            fuzzy_threshold=threshold,
            trained_at=datetime.now(),
            example_count=len(self._positive_examples) + len(self._negative_examples),
            accuracy=self._calculate_accuracy(),
        )

        if self.auto_save:
            self._save()

        return self._model

    def _optimize_threshold(self) -> float:
        """Optimize fuzzy matching threshold based on detection history."""
        if not self._detection_events:
            return 0.8  # Default

        # Count outcomes at different thresholds
        # For now, use a simple heuristic based on false positive/negative rates
        recent_events = self._detection_events[-50:]  # Last 50 events

        false_positives = sum(
            1 for e in recent_events
            if e.outcome == DetectionOutcome.FALSE_POSITIVE
        )
        false_negatives = sum(
            1 for e in recent_events
            if e.outcome == DetectionOutcome.FALSE_NEGATIVE
        )

        # If many false positives, increase threshold (stricter)
        # If many false negatives, decrease threshold (more lenient)
        current = self._model.fuzzy_threshold if self._model else 0.8

        fp_rate = false_positives / len(recent_events) if recent_events else 0
        fn_rate = false_negatives / len(recent_events) if recent_events else 0

        if fp_rate > 0.1:  # Too many false positives
            return min(0.95, current + 0.05)
        elif fn_rate > 0.1:  # Too many false negatives
            return max(0.6, current - 0.05)

        return current

    def _calculate_accuracy(self) -> float:
        """Calculate detection accuracy from recent events."""
        if not self._detection_events:
            return 0.0

        recent = self._detection_events[-50:]
        correct = sum(
            1 for e in recent
            if e.outcome in (DetectionOutcome.TRUE_POSITIVE, DetectionOutcome.TRUE_NEGATIVE)
        )
        return correct / len(recent)

    def get_model(self) -> Optional[WakeWordModel]:
        """Get the current wake word model."""
        return self._model

    def get_variations(self) -> list[str]:
        """Get all known wake word variations."""
        if self._model:
            return self._model.variations.copy()
        return self._generate_variations(self.primary_phrase)

    def get_status(self) -> TrainingStatus:
        """Get current training status."""
        positive_count = len(self._positive_examples)
        negative_count = len(self._negative_examples)
        total_detections = len(self._detection_events)
        accuracy = self._calculate_accuracy()

        # Determine phase
        if positive_count < self.MIN_POSITIVE_EXAMPLES:
            phase = TrainingPhase.NEEDS_EXAMPLES
            message = f"Need {self.MIN_POSITIVE_EXAMPLES - positive_count} more positive examples."
        elif positive_count < self.OPTIMAL_EXAMPLES:
            phase = TrainingPhase.COLLECTING
            message = f"Collecting examples. Have {positive_count}, optimal is {self.OPTIMAL_EXAMPLES}."
        elif self._model and self._model.trained_at:
            phase = TrainingPhase.READY
            message = f"Model ready with {len(self._model.variations)} variations. Accuracy: {accuracy:.0%}"
        else:
            phase = TrainingPhase.TRAINING
            message = "Processing training data."

        return TrainingStatus(
            phase=phase,
            positive_examples=positive_count,
            negative_examples=negative_count,
            total_detections=total_detections,
            accuracy=accuracy,
            message=message,
        )

    def get_statistics(self) -> dict:
        """Get training statistics."""
        accuracy = self._calculate_accuracy()

        # Outcome breakdown
        outcomes = Counter(e.outcome.value for e in self._detection_events)

        # Most matched variations
        matched = Counter(
            e.variation_matched for e in self._detection_events
            if e.variation_matched
        )

        return {
            "primary_phrase": self.primary_phrase,
            "positive_examples": len(self._positive_examples),
            "negative_examples": len(self._negative_examples),
            "total_detections": len(self._detection_events),
            "accuracy": accuracy,
            "outcome_breakdown": dict(outcomes),
            "top_matched_variations": matched.most_common(5),
            "total_variations": len(self._model.variations) if self._model else 0,
            "fuzzy_threshold": self._model.fuzzy_threshold if self._model else 0.8,
        }

    def set_primary_phrase(self, phrase: str) -> WakeWordModel:
        """
        Change the primary wake word phrase.

        Args:
            phrase: New primary phrase

        Returns:
            New WakeWordModel with generated variations
        """
        self.primary_phrase = phrase.lower().strip()

        # Clear training data (specific to old phrase)
        self._positive_examples.clear()
        self._negative_examples.clear()
        self._detection_events.clear()

        # Generate new model
        self._model = self._create_initial_model()

        if self.auto_save:
            self._save()

        return self._model

    def add_custom_variation(self, variation: str) -> None:
        """
        Add a custom variation manually.

        Args:
            variation: The variation text to add
        """
        if self._model:
            normalized = variation.lower().strip()
            if normalized not in self._model.variations:
                self._model.variations.append(normalized)
                self._model.variations.sort()

                if self.auto_save:
                    self._save()

    def remove_variation(self, variation: str) -> bool:
        """
        Remove a variation from the model.

        Args:
            variation: The variation to remove

        Returns:
            True if removed, False if not found
        """
        if self._model:
            normalized = variation.lower().strip()
            if normalized in self._model.variations:
                self._model.variations.remove(normalized)
                if self.auto_save:
                    self._save()
                return True
        return False

    def reset(self) -> None:
        """Reset all training data and start fresh."""
        self._positive_examples.clear()
        self._negative_examples.clear()
        self._detection_events.clear()
        self._model = self._create_initial_model()

        if self.auto_save:
            self._save()


# =============================================================================
# Module-level singleton
# =============================================================================

_trainer: Optional[WakeWordTrainer] = None


def get_wake_word_trainer() -> WakeWordTrainer:
    """Get the global wake word trainer instance."""
    global _trainer
    if _trainer is None:
        _trainer = WakeWordTrainer()
    return _trainer
