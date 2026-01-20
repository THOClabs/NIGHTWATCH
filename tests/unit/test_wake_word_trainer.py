"""
NIGHTWATCH Wake Word Trainer Tests

Tests for custom wake word training and personalization (Step 135).
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from services.voice.wake_word_trainer import (
    WakeWordTrainer,
    DetectionOutcome,
    TrainingPhase,
    WakeWordExample,
    DetectionEvent,
    WakeWordModel,
    TrainingStatus,
    get_wake_word_trainer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_data_path():
    """Create a temporary path for training data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_wake_word.json"


@pytest.fixture
def trainer(temp_data_path):
    """Create a WakeWordTrainer with temp storage."""
    return WakeWordTrainer(
        primary_phrase="nightwatch",
        data_path=temp_data_path,
    )


@pytest.fixture
def trainer_with_examples(trainer):
    """Create trainer with some examples."""
    trainer.add_positive_example("nightwatch", user_confirmed=True)
    trainer.add_positive_example("night watch", user_confirmed=True)
    trainer.add_positive_example("hey nightwatch", user_confirmed=True)
    trainer.add_negative_example("nice watch", user_confirmed=True)
    trainer.add_negative_example("night shift", user_confirmed=True)
    return trainer


# =============================================================================
# WakeWordExample Tests
# =============================================================================


class TestWakeWordExample:
    """Tests for WakeWordExample dataclass."""

    def test_example_creation(self):
        """Create a basic example."""
        example = WakeWordExample(
            text="nightwatch",
            is_positive=True,
        )
        assert example.text == "nightwatch"
        assert example.is_positive is True
        assert example.confidence == 1.0

    def test_example_with_confidence(self):
        """Create example with custom confidence."""
        example = WakeWordExample(
            text="night watch",
            is_positive=True,
            confidence=0.8,
            user_confirmed=True,
        )
        assert example.confidence == 0.8
        assert example.user_confirmed is True

    def test_example_to_dict(self):
        """Example converts to dict."""
        example = WakeWordExample(
            text="nightwatch",
            is_positive=True,
        )
        d = example.to_dict()
        assert d["text"] == "nightwatch"
        assert d["is_positive"] is True

    def test_example_from_dict(self):
        """Example creates from dict."""
        data = {
            "text": "nightwatch",
            "timestamp": "2025-01-15T22:30:00",
            "is_positive": True,
            "confidence": 0.9,
            "user_confirmed": True,
        }
        example = WakeWordExample.from_dict(data)
        assert example.text == "nightwatch"
        assert example.user_confirmed is True


# =============================================================================
# DetectionEvent Tests
# =============================================================================


class TestDetectionEvent:
    """Tests for DetectionEvent dataclass."""

    def test_event_creation(self):
        """Create a detection event."""
        event = DetectionEvent(
            text="hey nightwatch",
            detected=True,
            outcome=DetectionOutcome.TRUE_POSITIVE,
        )
        assert event.detected is True
        assert event.outcome == DetectionOutcome.TRUE_POSITIVE

    def test_event_with_variation(self):
        """Create event with matched variation."""
        event = DetectionEvent(
            text="hey nightwatch",
            detected=True,
            outcome=DetectionOutcome.TRUE_POSITIVE,
            variation_matched="hey nightwatch",
        )
        assert event.variation_matched == "hey nightwatch"

    def test_event_to_dict(self):
        """Event converts to dict."""
        event = DetectionEvent(
            text="nightwatch",
            detected=True,
            outcome=DetectionOutcome.TRUE_POSITIVE,
        )
        d = event.to_dict()
        assert d["detected"] is True
        assert d["outcome"] == "true_positive"

    def test_event_from_dict(self):
        """Event creates from dict."""
        data = {
            "text": "nightwatch",
            "detected": True,
            "outcome": "true_positive",
            "timestamp": "2025-01-15T22:30:00",
        }
        event = DetectionEvent.from_dict(data)
        assert event.outcome == DetectionOutcome.TRUE_POSITIVE


# =============================================================================
# WakeWordModel Tests
# =============================================================================


class TestWakeWordModel:
    """Tests for WakeWordModel dataclass."""

    def test_model_creation(self):
        """Create a wake word model."""
        model = WakeWordModel(
            primary_phrase="nightwatch",
            variations=["nightwatch", "night watch"],
        )
        assert model.primary_phrase == "nightwatch"
        assert len(model.variations) == 2

    def test_model_with_threshold(self):
        """Create model with custom threshold."""
        model = WakeWordModel(
            primary_phrase="nightwatch",
            fuzzy_threshold=0.85,
        )
        assert model.fuzzy_threshold == 0.85

    def test_model_to_dict(self):
        """Model converts to dict."""
        model = WakeWordModel(
            primary_phrase="nightwatch",
            variations=["nightwatch"],
            accuracy=0.95,
        )
        d = model.to_dict()
        assert d["primary_phrase"] == "nightwatch"
        assert d["accuracy"] == 0.95

    def test_model_from_dict(self):
        """Model creates from dict."""
        data = {
            "primary_phrase": "nightwatch",
            "variations": ["nightwatch", "night watch"],
            "fuzzy_threshold": 0.8,
            "trained_at": "2025-01-15T22:30:00",
            "accuracy": 0.9,
        }
        model = WakeWordModel.from_dict(data)
        assert model.primary_phrase == "nightwatch"
        assert len(model.variations) == 2


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Tests for trainer initialization."""

    def test_creates_initial_model(self, trainer):
        """Trainer creates initial model."""
        model = trainer.get_model()
        assert model is not None
        assert model.primary_phrase == "nightwatch"

    def test_generates_variations(self, trainer):
        """Initial model has generated variations."""
        variations = trainer.get_variations()
        assert len(variations) > 5  # Should have multiple variations
        assert "nightwatch" in variations

    def test_includes_prefixes(self, trainer):
        """Variations include common prefixes."""
        variations = trainer.get_variations()
        has_hey = any("hey" in v for v in variations)
        assert has_hey

    def test_includes_phonetic_variations(self, trainer):
        """Variations include phonetic alternatives."""
        variations = trainer.get_variations()
        # Should include phonetic variations like "nitewatch"
        has_phonetic = any("nite" in v for v in variations)
        assert has_phonetic


# =============================================================================
# Example Collection Tests
# =============================================================================


class TestExampleCollection:
    """Tests for collecting training examples."""

    def test_add_positive_example(self, trainer):
        """Add a positive example."""
        trainer.add_positive_example("nightwatch")
        status = trainer.get_status()
        assert status.positive_examples == 1

    def test_add_negative_example(self, trainer):
        """Add a negative example."""
        trainer.add_negative_example("nice watch")
        status = trainer.get_status()
        assert status.negative_examples == 1

    def test_confirmed_example_adds_variation(self, trainer):
        """User-confirmed example adds new variation."""
        initial_count = len(trainer.get_variations())
        trainer.add_positive_example("nite watch", user_confirmed=True)

        # Should add this as a variation
        variations = trainer.get_variations()
        assert "nite watch" in variations

    def test_collect_multiple_examples(self, trainer):
        """Collect multiple examples."""
        trainer.add_positive_example("nightwatch")
        trainer.add_positive_example("night watch")
        trainer.add_positive_example("hey nightwatch")
        trainer.add_negative_example("nice watch")

        status = trainer.get_status()
        assert status.positive_examples == 3
        assert status.negative_examples == 1


# =============================================================================
# Detection Recording Tests
# =============================================================================


class TestDetectionRecording:
    """Tests for recording detection events."""

    def test_record_true_positive(self, trainer):
        """Record a true positive detection."""
        trainer.record_detection(
            text="nightwatch",
            detected=True,
            was_correct=True,
        )
        stats = trainer.get_statistics()
        assert stats["total_detections"] == 1
        assert "true_positive" in stats["outcome_breakdown"]

    def test_record_false_positive(self, trainer):
        """Record a false positive detection."""
        trainer.record_detection(
            text="nice watch",
            detected=True,
            was_correct=False,
        )
        stats = trainer.get_statistics()
        assert "false_positive" in stats["outcome_breakdown"]

    def test_record_false_negative(self, trainer):
        """Record a false negative (missed detection)."""
        trainer.record_detection(
            text="nightwatch",
            detected=False,
            was_correct=False,
        )
        stats = trainer.get_statistics()
        assert "false_negative" in stats["outcome_breakdown"]

    def test_record_true_negative(self, trainer):
        """Record a true negative."""
        trainer.record_detection(
            text="hello world",
            detected=False,
            was_correct=True,
        )
        stats = trainer.get_statistics()
        assert "true_negative" in stats["outcome_breakdown"]

    def test_record_with_variation(self, trainer):
        """Record detection with matched variation."""
        trainer.record_detection(
            text="hey nightwatch",
            detected=True,
            was_correct=True,
            variation_matched="hey nightwatch",
        )
        stats = trainer.get_statistics()
        assert len(stats["top_matched_variations"]) > 0


# =============================================================================
# Training Tests
# =============================================================================


class TestTraining:
    """Tests for model training."""

    def test_train_model(self, trainer_with_examples):
        """Train model from examples."""
        model = trainer_with_examples.train()

        assert model is not None
        assert model.primary_phrase == "nightwatch"
        assert model.example_count > 0

    def test_training_adds_confirmed_examples(self, trainer):
        """Training incorporates confirmed examples."""
        trainer.add_positive_example("my nightwatch", user_confirmed=True)
        model = trainer.train()

        assert "my nightwatch" in model.variations

    def test_training_removes_negative_examples(self, trainer):
        """Training excludes negative examples."""
        trainer.add_positive_example("nightwatch", user_confirmed=True)
        trainer.add_negative_example("night shift", user_confirmed=True)
        model = trainer.train()

        assert "night shift" not in model.variations

    def test_accuracy_calculation(self, trainer):
        """Accuracy is calculated from detection events."""
        # Add some detection events
        for _ in range(8):
            trainer.record_detection("nightwatch", True, True)
        for _ in range(2):
            trainer.record_detection("nice watch", True, False)

        stats = trainer.get_statistics()
        assert stats["accuracy"] == 0.8  # 8/10


# =============================================================================
# Status Tests
# =============================================================================


class TestTrainingStatus:
    """Tests for training status."""

    def test_needs_examples_phase(self, trainer):
        """Status shows needs examples when few collected."""
        status = trainer.get_status()
        assert status.phase == TrainingPhase.NEEDS_EXAMPLES

    def test_collecting_phase(self, trainer):
        """Status shows collecting with some examples."""
        for i in range(5):
            trainer.add_positive_example(f"nightwatch {i}")

        status = trainer.get_status()
        assert status.phase in (TrainingPhase.COLLECTING, TrainingPhase.READY)

    def test_ready_phase(self, trainer_with_examples):
        """Status shows ready after training with enough examples."""
        # Add more examples to reach OPTIMAL threshold
        for i in range(10):
            trainer_with_examples.add_positive_example(f"nightwatch test {i}")

        trainer_with_examples.train()
        status = trainer_with_examples.get_status()

        assert status.phase == TrainingPhase.READY

    def test_status_to_dict(self, trainer):
        """Status converts to dict."""
        status = trainer.get_status()
        d = status.to_dict()

        assert "phase" in d
        assert "positive_examples" in d
        assert "message" in d


# =============================================================================
# Variation Management Tests
# =============================================================================


class TestVariationManagement:
    """Tests for managing wake word variations."""

    def test_add_custom_variation(self, trainer):
        """Add a custom variation."""
        trainer.add_custom_variation("hey hey nightwatch")
        variations = trainer.get_variations()
        assert "hey hey nightwatch" in variations

    def test_remove_variation(self, trainer):
        """Remove a variation."""
        trainer.add_custom_variation("remove me")
        assert "remove me" in trainer.get_variations()

        removed = trainer.remove_variation("remove me")
        assert removed is True
        assert "remove me" not in trainer.get_variations()

    def test_remove_nonexistent_variation(self, trainer):
        """Remove non-existent variation returns False."""
        removed = trainer.remove_variation("doesnt exist")
        assert removed is False

    def test_change_primary_phrase(self, trainer):
        """Change the primary wake phrase."""
        model = trainer.set_primary_phrase("computer")

        assert trainer.primary_phrase == "computer"
        assert model.primary_phrase == "computer"
        assert "computer" in model.variations


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for training data persistence."""

    def test_data_saved(self, temp_data_path):
        """Training data is saved to disk."""
        trainer = WakeWordTrainer(data_path=temp_data_path)
        trainer.add_positive_example("nightwatch")

        assert temp_data_path.exists()

    def test_data_loaded(self, temp_data_path):
        """Training data is loaded from disk."""
        # Create and save
        trainer1 = WakeWordTrainer(data_path=temp_data_path)
        trainer1.add_positive_example("nightwatch", user_confirmed=True)
        trainer1.add_positive_example("night watch", user_confirmed=True)

        # Create new instance, should load
        trainer2 = WakeWordTrainer(data_path=temp_data_path)

        status = trainer2.get_status()
        assert status.positive_examples == 2

    def test_model_persisted(self, temp_data_path):
        """Trained model is persisted."""
        trainer1 = WakeWordTrainer(data_path=temp_data_path)
        trainer1.add_positive_example("nightwatch")
        trainer1.add_positive_example("night watch")
        trainer1.add_positive_example("hey nightwatch")
        trainer1.train()

        trainer2 = WakeWordTrainer(data_path=temp_data_path)
        model = trainer2.get_model()

        assert model is not None
        assert model.example_count > 0

    def test_reset_clears_data(self, trainer_with_examples):
        """Reset clears all training data."""
        trainer_with_examples.reset()

        status = trainer_with_examples.get_status()
        assert status.positive_examples == 0
        assert status.negative_examples == 0
        assert status.total_detections == 0


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for training statistics."""

    def test_get_statistics(self, trainer_with_examples):
        """Get training statistics."""
        stats = trainer_with_examples.get_statistics()

        assert "primary_phrase" in stats
        assert "positive_examples" in stats
        assert "negative_examples" in stats
        assert "total_variations" in stats
        assert "fuzzy_threshold" in stats

    def test_statistics_count_examples(self, trainer_with_examples):
        """Statistics reflect example counts."""
        stats = trainer_with_examples.get_statistics()

        assert stats["positive_examples"] == 3
        assert stats["negative_examples"] == 2


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_detection_outcomes(self):
        """All detection outcomes defined."""
        assert DetectionOutcome.TRUE_POSITIVE.value == "true_positive"
        assert DetectionOutcome.FALSE_POSITIVE.value == "false_positive"
        assert DetectionOutcome.FALSE_NEGATIVE.value == "false_negative"
        assert DetectionOutcome.TRUE_NEGATIVE.value == "true_negative"

    def test_training_phases(self):
        """All training phases defined."""
        assert TrainingPhase.COLLECTING.value == "collecting"
        assert TrainingPhase.TRAINING.value == "training"
        assert TrainingPhase.READY.value == "ready"
        assert TrainingPhase.NEEDS_EXAMPLES.value == "needs_examples"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_wake_word_trainer_returns_singleton(self):
        """get_wake_word_trainer returns same instance."""
        t1 = get_wake_word_trainer()
        t2 = get_wake_word_trainer()
        assert t1 is t2

    def test_get_wake_word_trainer_creates_instance(self):
        """get_wake_word_trainer creates instance."""
        trainer = get_wake_word_trainer()
        assert isinstance(trainer, WakeWordTrainer)
