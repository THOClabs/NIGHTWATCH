"""
NIGHTWATCH Vocabulary Trainer Tests

Tests for fine-tuned astronomy vocabulary learning and optimization (Step 134).
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from services.voice.vocabulary_trainer import (
    VocabularyTrainer,
    TermCategory,
    TermUsage,
    NormalizationRule,
    VocabularyExport,
    get_vocabulary_trainer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_vocab_path():
    """Create a temporary path for vocabulary file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_vocab.json"


@pytest.fixture
def trainer(temp_vocab_path):
    """Create a VocabularyTrainer with temp storage."""
    return VocabularyTrainer(vocab_path=temp_vocab_path)


@pytest.fixture
def trainer_with_usage(trainer):
    """Create trainer with some recorded usage."""
    trainer.record_usage("M31", success=True)
    trainer.record_usage("M31", success=True)
    trainer.record_usage("M31", success=True)
    trainer.record_usage("M42", success=True)
    trainer.record_usage("M42", success=False)
    trainer.record_usage("Polaris", success=True)
    return trainer


# =============================================================================
# TermUsage Tests
# =============================================================================


class TestTermUsage:
    """Tests for TermUsage dataclass."""

    def test_usage_creation(self):
        """Create a basic term usage."""
        usage = TermUsage(
            term="M31",
            category=TermCategory.MESSIER,
        )
        assert usage.term == "M31"
        assert usage.category == TermCategory.MESSIER
        assert usage.use_count == 0

    def test_success_rate_calculation(self):
        """Success rate calculates correctly."""
        usage = TermUsage(
            term="M31",
            category=TermCategory.MESSIER,
            use_count=10,
            success_count=8,
        )
        assert usage.success_rate == 0.8

    def test_success_rate_zero_uses(self):
        """Success rate is 0 with no uses."""
        usage = TermUsage(term="M31", category=TermCategory.MESSIER)
        assert usage.success_rate == 0.0

    def test_boost_weight_calculation(self):
        """Boost weight combines usage and success."""
        usage = TermUsage(
            term="M31",
            category=TermCategory.MESSIER,
            use_count=20,
            success_count=18,
            last_used=datetime.now(),
        )
        weight = usage.boost_weight
        assert weight > 1.0  # Frequent, successful, recent

    def test_boost_weight_decays_with_time(self):
        """Boost weight decreases for old terms."""
        recent = TermUsage(
            term="M31",
            category=TermCategory.MESSIER,
            use_count=10,
            success_count=10,
            last_used=datetime.now(),
        )
        old = TermUsage(
            term="M42",
            category=TermCategory.MESSIER,
            use_count=10,
            success_count=10,
            last_used=datetime.now() - timedelta(days=30),
        )
        assert recent.boost_weight > old.boost_weight

    def test_to_dict(self):
        """Term usage converts to dict."""
        usage = TermUsage(
            term="M31",
            category=TermCategory.MESSIER,
            use_count=5,
            success_count=4,
        )
        d = usage.to_dict()
        assert d["term"] == "M31"
        assert d["category"] == "messier"
        assert d["use_count"] == 5

    def test_from_dict(self):
        """Term usage creates from dict."""
        data = {
            "term": "M31",
            "category": "messier",
            "use_count": 5,
            "success_count": 4,
            "last_used": "2025-01-15T22:30:00",
            "added_at": "2025-01-01T00:00:00",
            "custom": False,
        }
        usage = TermUsage.from_dict(data)
        assert usage.term == "M31"
        assert usage.use_count == 5
        assert usage.last_used is not None


# =============================================================================
# NormalizationRule Tests
# =============================================================================


class TestNormalizationRule:
    """Tests for NormalizationRule dataclass."""

    def test_rule_creation(self):
        """Create a normalization rule."""
        rule = NormalizationRule(
            pattern=r"m\s*(\d+)",
            replacement=r"M\1",
        )
        assert rule.pattern == r"m\s*(\d+)"

    def test_apply_rule(self):
        """Apply normalization to text."""
        rule = NormalizationRule(
            pattern=r"m\s*(\d+)",
            replacement=r"M\1",
        )
        result = rule.apply("slew to m 31")
        assert result == "slew to M31"

    def test_apply_case_insensitive(self):
        """Rules are case insensitive."""
        rule = NormalizationRule(
            pattern=r"messier\s*(\d+)",
            replacement=r"M\1",
        )
        result = rule.apply("goto MESSIER 42")
        assert result == "goto M42"

    def test_apply_betelgeuse(self):
        """Common mishearing normalization."""
        rule = NormalizationRule(
            pattern=r"beetle\s*juice",
            replacement="Betelgeuse",
        )
        result = rule.apply("slew to beetle juice")
        assert result == "slew to Betelgeuse"

    def test_to_dict(self):
        """Rule converts to dict."""
        rule = NormalizationRule(
            pattern=r"m\s*(\d+)",
            replacement=r"M\1",
            use_count=10,
        )
        d = rule.to_dict()
        assert d["pattern"] == r"m\s*(\d+)"
        assert d["use_count"] == 10


# =============================================================================
# Default Initialization Tests
# =============================================================================


class TestDefaultInitialization:
    """Tests for default vocabulary initialization."""

    def test_initialized_with_defaults(self, trainer):
        """Trainer initializes with default vocabulary."""
        stats = trainer.get_statistics()
        assert stats["total_terms"] > 100  # Should have many default terms

    def test_has_messier_objects(self, trainer):
        """Default vocabulary includes Messier objects."""
        term = trainer.get_term("M31")
        assert term is not None
        assert term.category == TermCategory.MESSIER

    def test_has_stars(self, trainer):
        """Default vocabulary includes stars."""
        term = trainer.get_term("Polaris")
        assert term is not None
        assert term.category == TermCategory.STAR

    def test_has_constellations(self, trainer):
        """Default vocabulary includes constellations."""
        term = trainer.get_term("Orion")
        assert term is not None
        assert term.category == TermCategory.CONSTELLATION

    def test_has_commands(self, trainer):
        """Default vocabulary includes commands."""
        term = trainer.get_term("slew")
        assert term is not None
        assert term.category == TermCategory.COMMAND

    def test_has_default_normalizations(self, trainer):
        """Has default normalization rules."""
        stats = trainer.get_statistics()
        assert stats["normalization_rules"] > 0


# =============================================================================
# Usage Recording Tests
# =============================================================================


class TestUsageRecording:
    """Tests for recording vocabulary usage."""

    def test_record_usage(self, trainer):
        """Record usage of existing term."""
        trainer.record_usage("M31", success=True)
        term = trainer.get_term("M31")
        assert term.use_count >= 1
        assert term.last_used is not None

    def test_record_multiple_uses(self, trainer):
        """Multiple uses accumulate."""
        trainer.record_usage("M31", success=True)
        trainer.record_usage("M31", success=True)
        trainer.record_usage("M31", success=False)

        term = trainer.get_term("M31")
        assert term.use_count >= 3
        assert term.success_count >= 2

    def test_record_new_term(self, trainer):
        """Recording unknown term adds it."""
        trainer.record_usage("CustomTarget123", success=True)

        term = trainer.get_term("CustomTarget123")
        assert term is not None
        assert term.custom is True
        assert term.category == TermCategory.CUSTOM

    def test_record_with_category(self, trainer):
        """New terms get specified category."""
        trainer.record_usage(
            "MyNebula",
            success=True,
            category=TermCategory.NGC_IC,
        )

        term = trainer.get_term("MyNebula")
        assert term.category == TermCategory.NGC_IC


# =============================================================================
# Term Management Tests
# =============================================================================


class TestTermManagement:
    """Tests for term management functions."""

    def test_add_term(self, trainer):
        """Add a new custom term."""
        trainer.add_term("CustomStar", category=TermCategory.STAR)

        term = trainer.get_term("CustomStar")
        assert term is not None
        assert term.custom is True

    def test_add_duplicate_term(self, trainer):
        """Adding duplicate term does not create duplicate."""
        trainer.add_term("NewTerm")
        trainer.add_term("NewTerm")

        # Should still have only one
        terms = [t for t in trainer._terms.values() if t.term == "NewTerm"]
        assert len(terms) == 1

    def test_get_terms_by_category(self, trainer):
        """Get all terms in a category."""
        messier = trainer.get_terms_by_category(TermCategory.MESSIER)
        assert len(messier) > 10
        assert all(t.category == TermCategory.MESSIER for t in messier)

    def test_get_top_terms(self, trainer_with_usage):
        """Get most frequently used terms."""
        top = trainer_with_usage.get_top_terms(limit=3)

        # M31 should be first (3 uses)
        assert top[0].term == "M31"
        assert len(top) <= 3


# =============================================================================
# Normalization Tests
# =============================================================================


class TestNormalization:
    """Tests for text normalization."""

    def test_normalize_messier(self, trainer):
        """Normalize Messier object variations."""
        result = trainer.normalize_text("slew to m 31")
        assert "M31" in result

    def test_normalize_ngc(self, trainer):
        """Normalize NGC object variations."""
        result = trainer.normalize_text("goto ngc 7000")
        assert "NGC 7000" in result

    def test_normalize_betelgeuse(self, trainer):
        """Normalize Betelgeuse mishearing."""
        result = trainer.normalize_text("point at beetle juice")
        assert "Betelgeuse" in result

    def test_normalize_goto_command(self, trainer):
        """Normalize goto command variations."""
        result = trainer.normalize_text("go to M31")
        assert "goto" in result

    def test_add_normalization(self, trainer):
        """Add custom normalization rule."""
        trainer.add_normalization(
            r"my\s*target",
            "MyTarget",
        )
        result = trainer.normalize_text("slew to my target")
        assert "MyTarget" in result


# =============================================================================
# Learning Tests
# =============================================================================


class TestLearning:
    """Tests for vocabulary learning."""

    def test_learn_from_correction(self, trainer):
        """Learn from user correction."""
        rule = trainer.learn_from_correction(
            misheard="vague a",
            correct="Vega",
        )

        assert rule is not None
        assert rule.replacement == "Vega"

        # Should normalize now
        result = trainer.normalize_text("slew to vague a")
        assert "Vega" in result

    def test_suggest_normalization(self, trainer):
        """Suggest pattern for mishearing."""
        pattern = trainer.suggest_normalization("beetle juice", "Betelgeuse")

        # Should create a usable pattern
        assert "beetle" in pattern.lower()

    def test_get_problem_terms(self, trainer):
        """Get terms with low success rate."""
        # Create a problem term
        for _ in range(10):
            trainer.record_usage("ProblemTerm", success=False)

        problems = trainer.get_problem_terms()
        problem_terms = [t.term for t in problems]
        assert "ProblemTerm" in problem_terms


# =============================================================================
# Export Tests
# =============================================================================


class TestExport:
    """Tests for vocabulary export."""

    def test_get_boosted_vocabulary(self, trainer_with_usage):
        """Export weighted vocabulary."""
        export = trainer_with_usage.get_boosted_vocabulary()

        assert len(export.terms) > 0
        assert len(export.weights) == len(export.terms)
        assert export.generated_at is not None

    def test_export_weights_ordered(self, trainer_with_usage):
        """Export weights are in descending order."""
        export = trainer_with_usage.get_boosted_vocabulary()

        # Most used terms should be first
        assert "M31" in export.terms[:10]

    def test_export_to_dict(self, trainer_with_usage):
        """Export converts to dict."""
        export = trainer_with_usage.get_boosted_vocabulary()
        d = export.to_dict()

        assert "terms" in d
        assert "weights" in d
        assert "normalizations" in d


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for vocabulary statistics."""

    def test_get_statistics(self, trainer_with_usage):
        """Get vocabulary statistics."""
        stats = trainer_with_usage.get_statistics()

        assert "total_terms" in stats
        assert "custom_terms" in stats
        assert "total_uses" in stats
        assert "category_breakdown" in stats
        assert "top_terms" in stats

    def test_statistics_reflect_usage(self, trainer_with_usage):
        """Statistics reflect recorded usage."""
        stats = trainer_with_usage.get_statistics()

        # Should have at least the recorded uses
        assert stats["total_uses"] >= 6  # 3 + 2 + 1


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for vocabulary persistence."""

    def test_vocabulary_saved(self, temp_vocab_path):
        """Vocabulary is saved to disk."""
        trainer = VocabularyTrainer(vocab_path=temp_vocab_path)
        trainer.record_usage("M31", success=True)

        assert temp_vocab_path.exists()

    def test_vocabulary_loaded(self, temp_vocab_path):
        """Vocabulary is loaded from disk."""
        # Create and save
        trainer1 = VocabularyTrainer(vocab_path=temp_vocab_path)
        trainer1.record_usage("TestTerm", success=True, category=TermCategory.CUSTOM)
        trainer1.record_usage("TestTerm", success=True)

        # Create new instance, should load
        trainer2 = VocabularyTrainer(vocab_path=temp_vocab_path)

        term = trainer2.get_term("TestTerm")
        assert term is not None
        assert term.use_count == 2

    def test_reset_statistics(self, trainer_with_usage):
        """Reset clears usage statistics."""
        trainer_with_usage.reset_statistics()

        term = trainer_with_usage.get_term("M31")
        assert term.use_count == 0
        assert term.success_count == 0

    def test_clear_custom(self, trainer):
        """Clear removes custom terms."""
        trainer.add_term("CustomTerm")
        trainer.add_normalization(r"custom", "Custom")

        trainer.clear_custom()

        assert trainer.get_term("CustomTerm") is None


# =============================================================================
# Category Tests
# =============================================================================


class TestTermCategory:
    """Tests for TermCategory enum."""

    def test_all_categories_exist(self):
        """All expected categories are defined."""
        assert TermCategory.MESSIER.value == "messier"
        assert TermCategory.NGC_IC.value == "ngc_ic"
        assert TermCategory.STAR.value == "star"
        assert TermCategory.CONSTELLATION.value == "constellation"
        assert TermCategory.PLANET.value == "planet"
        assert TermCategory.COMMAND.value == "command"
        assert TermCategory.EQUIPMENT.value == "equipment"
        assert TermCategory.COORDINATE.value == "coordinate"
        assert TermCategory.CUSTOM.value == "custom"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_vocabulary_trainer_returns_singleton(self):
        """get_vocabulary_trainer returns same instance."""
        t1 = get_vocabulary_trainer()
        t2 = get_vocabulary_trainer()
        assert t1 is t2

    def test_get_vocabulary_trainer_creates_instance(self):
        """get_vocabulary_trainer creates instance."""
        trainer = get_vocabulary_trainer()
        assert isinstance(trainer, VocabularyTrainer)
