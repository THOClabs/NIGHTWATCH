"""
NIGHTWATCH Voice Services

Voice processing services including vocabulary training and optimization.
"""

from .vocabulary_trainer import (
    VocabularyTrainer,
    TermCategory,
    TermUsage,
    NormalizationRule,
    VocabularyExport,
    get_vocabulary_trainer,
)

from .wake_word_trainer import (
    WakeWordTrainer,
    DetectionOutcome,
    TrainingPhase,
    WakeWordExample,
    DetectionEvent,
    WakeWordModel,
    TrainingStatus,
    get_wake_word_trainer,
)

__all__ = [
    # Vocabulary Training
    "VocabularyTrainer",
    "TermCategory",
    "TermUsage",
    "NormalizationRule",
    "VocabularyExport",
    "get_vocabulary_trainer",
    # Wake Word Training
    "WakeWordTrainer",
    "DetectionOutcome",
    "TrainingPhase",
    "WakeWordExample",
    "DetectionEvent",
    "WakeWordModel",
    "TrainingStatus",
    "get_wake_word_trainer",
]
