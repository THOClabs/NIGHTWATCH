"""
NIGHTWATCH Vocabulary Trainer

Fine-tuned astronomy vocabulary with learning and optimization (Step 134).

This module provides:
- Dynamic vocabulary learning from user commands
- Frequency-weighted term boosting for STT
- Custom astronomy normalization patterns
- Vocabulary effectiveness tracking
- Export for STT model vocabulary boost
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


class TermCategory(Enum):
    """Categories of astronomy vocabulary terms."""

    MESSIER = "messier"
    NGC_IC = "ngc_ic"
    CALDWELL = "caldwell"
    STAR = "star"
    CONSTELLATION = "constellation"
    PLANET = "planet"
    COMMAND = "command"
    EQUIPMENT = "equipment"
    COORDINATE = "coordinate"
    CUSTOM = "custom"


# Default astronomy vocabulary with categories
DEFAULT_VOCABULARY = {
    TermCategory.MESSIER: [
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10",
        "M11", "M12", "M13", "M14", "M15", "M16", "M17", "M18", "M19", "M20",
        "M27", "M31", "M32", "M33", "M42", "M43", "M44", "M45", "M51", "M52",
        "M57", "M63", "M64", "M65", "M66", "M67", "M81", "M82", "M83", "M87",
        "M92", "M97", "M101", "M104", "M106", "M110", "Messier",
    ],
    TermCategory.NGC_IC: [
        "NGC", "IC", "NGC 7000", "NGC 6992", "NGC 6960", "NGC 2237",
        "NGC 869", "NGC 884", "NGC 457", "NGC 7331", "NGC 253",
    ],
    TermCategory.CALDWELL: [
        "Caldwell", "C14", "C33", "C38", "C39", "C41", "C49", "C55",
    ],
    TermCategory.STAR: [
        "Polaris", "Vega", "Sirius", "Betelgeuse", "Rigel", "Arcturus",
        "Aldebaran", "Antares", "Deneb", "Altair", "Capella", "Procyon",
        "Spica", "Fomalhaut", "Regulus", "Canopus", "Achernar", "Hadar",
        "Mimosa", "Bellatrix", "Alnilam", "Alnitak", "Mintaka",
    ],
    TermCategory.CONSTELLATION: [
        "Orion", "Andromeda", "Cassiopeia", "Ursa Major", "Ursa Minor",
        "Cygnus", "Lyra", "Sagittarius", "Scorpius", "Leo", "Gemini",
        "Taurus", "Perseus", "Pegasus", "Aquila", "Draco", "Hercules",
        "Cepheus", "Virgo", "Aquarius", "Pisces", "Aries", "Cancer",
        "Capricornus", "Libra", "Ophiuchus", "Serpens", "Centaurus",
    ],
    TermCategory.PLANET: [
        "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",
        "Moon", "Luna", "Sol", "Sun",
    ],
    TermCategory.COMMAND: [
        "slew", "goto", "track", "park", "unpark", "sync", "focus",
        "exposure", "capture", "abort", "stop", "calibrate", "center",
        "guide", "dither", "plate solve", "meridian flip",
    ],
    TermCategory.EQUIPMENT: [
        "telescope", "mount", "camera", "focuser", "filter", "guider",
        "autoguider", "dome", "roof", "flat", "dark", "bias", "CCD",
        "CMOS", "eyepiece", "Barlow", "reducer", "corrector",
    ],
    TermCategory.COORDINATE: [
        "right ascension", "declination", "altitude", "azimuth",
        "RA", "Dec", "Alt", "Az", "epoch", "J2000", "B1950",
        "hour angle", "zenith", "nadir", "meridian",
    ],
}


# Default normalizations for common speech variations
DEFAULT_NORMALIZATIONS = {
    # Messier with spaces
    r"m\s*(\d+)": r"M\1",
    r"messier\s*(\d+)": r"M\1",
    # NGC with spaces
    r"n\s*g\s*c\s*(\d+)": r"NGC \1",
    r"ngc\s*(\d+)": r"NGC \1",
    # IC with spaces
    r"i\s*c\s*(\d+)": r"IC \1",
    # Caldwell (use word boundary to avoid matching inside NGC)
    r"caldwell\s*(\d+)": r"C\1",
    r"\bc\s*(\d+)": r"C\1",
    # Common mishearings
    r"beetle\s*juice": "Betelgeuse",
    r"beetle\s*guys": "Betelgeuse",
    r"vague?a": "Vega",
    r"serious": "Sirius",
    r"polaris\s*star": "Polaris",
    r"north\s*star": "Polaris",
    # Command variations
    r"go\s*to": "goto",
    r"point\s*(at|to)": r"slew to",
    r"aim\s*(at|to)": r"slew to",
    r"move\s*to": r"slew to",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TermUsage:
    """Track usage statistics for a vocabulary term."""

    term: str
    category: TermCategory
    use_count: int = 0
    success_count: int = 0  # Times recognition was correct
    last_used: Optional[datetime] = None
    added_at: Optional[datetime] = None
    custom: bool = False

    @property
    def success_rate(self) -> float:
        """Calculate recognition success rate."""
        if self.use_count == 0:
            return 0.0
        return self.success_count / self.use_count

    @property
    def boost_weight(self) -> float:
        """Calculate boost weight based on usage and success."""
        # Base weight from usage frequency
        frequency_weight = min(1.0 + (self.use_count / 50), 2.0)

        # Success modifier
        success_modifier = 0.5 + 0.5 * self.success_rate

        # Recency boost (decay over 30 days)
        recency_boost = 1.0
        if self.last_used:
            days_ago = (datetime.now() - self.last_used).days
            recency_boost = max(0.5, 1.0 - (days_ago / 60))

        return frequency_weight * success_modifier * recency_boost

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "term": self.term,
            "category": self.category.value,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TermUsage":
        """Create from dictionary."""
        return cls(
            term=data["term"],
            category=TermCategory(data["category"]),
            use_count=data.get("use_count", 0),
            success_count=data.get("success_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            added_at=datetime.fromisoformat(data["added_at"]) if data.get("added_at") else None,
            custom=data.get("custom", False),
        )


@dataclass
class NormalizationRule:
    """A text normalization rule for speech recognition."""

    pattern: str  # Regex pattern
    replacement: str  # Replacement (can use groups)
    use_count: int = 0
    success_count: int = 0
    custom: bool = False

    @property
    def compiled_pattern(self) -> re.Pattern:
        """Get compiled regex pattern."""
        return re.compile(self.pattern, re.IGNORECASE)

    def apply(self, text: str) -> str:
        """Apply normalization to text."""
        return self.compiled_pattern.sub(self.replacement, text)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern,
            "replacement": self.replacement,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NormalizationRule":
        """Create from dictionary."""
        return cls(
            pattern=data["pattern"],
            replacement=data["replacement"],
            use_count=data.get("use_count", 0),
            success_count=data.get("success_count", 0),
            custom=data.get("custom", False),
        )


@dataclass
class VocabularyExport:
    """Export format for STT vocabulary boost."""

    terms: list[str]
    weights: list[float]
    normalizations: dict[str, str]
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "terms": self.terms,
            "weights": self.weights,
            "normalizations": self.normalizations,
            "generated_at": self.generated_at.isoformat(),
        }


# =============================================================================
# Vocabulary Trainer
# =============================================================================


class VocabularyTrainer:
    """
    Learns and optimizes astronomy vocabulary from user interactions.

    Features:
    - Track term usage frequency and success
    - Learn new terms from user commands
    - Generate weighted vocabulary for STT boost
    - Manage normalization rules
    - Export vocabulary for model integration
    """

    def __init__(
        self,
        vocab_path: Optional[Path] = None,
        auto_save: bool = True,
    ):
        """
        Initialize vocabulary trainer.

        Args:
            vocab_path: Path to vocabulary data file
            auto_save: Whether to auto-save after updates
        """
        self.vocab_path = vocab_path or Path.home() / ".nightwatch" / "vocabulary.json"
        self.auto_save = auto_save

        # Term tracking
        self._terms: dict[str, TermUsage] = {}

        # Normalization rules
        self._normalizations: list[NormalizationRule] = []

        # Load existing data
        self._load()

        # Initialize with defaults if empty
        if not self._terms:
            self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize with default vocabulary."""
        now = datetime.now()

        for category, terms in DEFAULT_VOCABULARY.items():
            for term in terms:
                key = term.lower()
                self._terms[key] = TermUsage(
                    term=term,
                    category=category,
                    added_at=now,
                    custom=False,
                )

        for pattern, replacement in DEFAULT_NORMALIZATIONS.items():
            self._normalizations.append(NormalizationRule(
                pattern=pattern,
                replacement=replacement,
                custom=False,
            ))

    def _load(self) -> None:
        """Load vocabulary from disk."""
        if not self.vocab_path.exists():
            return

        try:
            with open(self.vocab_path) as f:
                data = json.load(f)

            # Load terms
            for term_data in data.get("terms", []):
                usage = TermUsage.from_dict(term_data)
                self._terms[usage.term.lower()] = usage

            # Load normalizations
            for norm_data in data.get("normalizations", []):
                self._normalizations.append(NormalizationRule.from_dict(norm_data))

        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        """Save vocabulary to disk."""
        self.vocab_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "terms": [t.to_dict() for t in self._terms.values()],
            "normalizations": [n.to_dict() for n in self._normalizations],
            "saved_at": datetime.now().isoformat(),
        }

        with open(self.vocab_path, "w") as f:
            json.dump(data, f, indent=2)

    def record_usage(
        self,
        term: str,
        success: bool = True,
        category: Optional[TermCategory] = None,
    ) -> None:
        """
        Record usage of a vocabulary term.

        Args:
            term: The term that was used
            success: Whether recognition was successful
            category: Category for new terms
        """
        key = term.lower()

        if key in self._terms:
            usage = self._terms[key]
            usage.use_count += 1
            if success:
                usage.success_count += 1
            usage.last_used = datetime.now()
        else:
            # Learn new term
            self._terms[key] = TermUsage(
                term=term,
                category=category or TermCategory.CUSTOM,
                use_count=1,
                success_count=1 if success else 0,
                last_used=datetime.now(),
                added_at=datetime.now(),
                custom=True,
            )

        if self.auto_save:
            self._save()

    def add_term(
        self,
        term: str,
        category: TermCategory = TermCategory.CUSTOM,
    ) -> None:
        """
        Add a new vocabulary term.

        Args:
            term: The term to add
            category: Term category
        """
        key = term.lower()
        if key not in self._terms:
            self._terms[key] = TermUsage(
                term=term,
                category=category,
                added_at=datetime.now(),
                custom=True,
            )

            if self.auto_save:
                self._save()

    def add_normalization(
        self,
        pattern: str,
        replacement: str,
    ) -> None:
        """
        Add a custom normalization rule.

        Args:
            pattern: Regex pattern to match
            replacement: Replacement string
        """
        # Check for duplicates
        for rule in self._normalizations:
            if rule.pattern == pattern:
                rule.replacement = replacement
                if self.auto_save:
                    self._save()
                return

        self._normalizations.append(NormalizationRule(
            pattern=pattern,
            replacement=replacement,
            custom=True,
        ))

        if self.auto_save:
            self._save()

    def normalize_text(self, text: str) -> str:
        """
        Apply all normalization rules to text.

        Args:
            text: Input text from speech recognition

        Returns:
            Normalized text
        """
        result = text
        for rule in self._normalizations:
            try:
                new_result = rule.apply(result)
                if new_result != result:
                    rule.use_count += 1
                result = new_result
            except re.error:
                pass
        return result

    def get_term(self, term: str) -> Optional[TermUsage]:
        """Get usage data for a term."""
        return self._terms.get(term.lower())

    def get_terms_by_category(self, category: TermCategory) -> list[TermUsage]:
        """Get all terms in a category."""
        return [t for t in self._terms.values() if t.category == category]

    def get_top_terms(self, limit: int = 50) -> list[TermUsage]:
        """Get most frequently used terms."""
        sorted_terms = sorted(
            self._terms.values(),
            key=lambda t: t.use_count,
            reverse=True,
        )
        return sorted_terms[:limit]

    def get_boosted_vocabulary(self) -> VocabularyExport:
        """
        Generate weighted vocabulary for STT boost.

        Returns:
            VocabularyExport with terms, weights, and normalizations
        """
        # Sort terms by boost weight
        sorted_terms = sorted(
            self._terms.values(),
            key=lambda t: t.boost_weight,
            reverse=True,
        )

        terms = [t.term for t in sorted_terms]
        weights = [t.boost_weight for t in sorted_terms]

        # Build normalizations dict
        normalizations = {}
        for rule in self._normalizations:
            # For simple patterns, use as key
            if not any(c in rule.pattern for c in r".*+?[](){}|^$\\"):
                normalizations[rule.pattern] = rule.replacement

        return VocabularyExport(
            terms=terms,
            weights=weights,
            normalizations=normalizations,
        )

    def get_statistics(self) -> dict:
        """Get vocabulary statistics."""
        total_terms = len(self._terms)
        custom_terms = sum(1 for t in self._terms.values() if t.custom)
        total_uses = sum(t.use_count for t in self._terms.values())

        # Category breakdown
        category_counts = Counter(t.category.value for t in self._terms.values())

        # Most used
        top_terms = self.get_top_terms(5)

        # Recent activity
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        recent_uses = sum(
            1 for t in self._terms.values()
            if t.last_used and t.last_used > week_ago
        )

        return {
            "total_terms": total_terms,
            "custom_terms": custom_terms,
            "total_uses": total_uses,
            "normalization_rules": len(self._normalizations),
            "category_breakdown": dict(category_counts),
            "top_terms": [
                {"term": t.term, "uses": t.use_count}
                for t in top_terms
            ],
            "terms_used_this_week": recent_uses,
        }

    def get_problem_terms(self) -> list[TermUsage]:
        """
        Get terms with low recognition success.

        Returns:
            List of terms with <70% success rate and >5 uses
        """
        return [
            t for t in self._terms.values()
            if t.use_count >= 5 and t.success_rate < 0.7
        ]

    def suggest_normalization(self, misheard: str, correct: str) -> str:
        """
        Suggest a normalization pattern for a misheard term.

        Args:
            misheard: What was heard
            correct: What should have been

        Returns:
            Suggested regex pattern
        """
        # Escape special regex characters
        pattern = re.escape(misheard.lower())

        # Allow flexible spacing
        pattern = pattern.replace(r"\ ", r"\s*")

        return pattern

    def learn_from_correction(
        self,
        misheard: str,
        correct: str,
        auto_add_rule: bool = True,
    ) -> Optional[NormalizationRule]:
        """
        Learn from a user correction.

        Args:
            misheard: What was recognized incorrectly
            correct: What the user meant
            auto_add_rule: Whether to automatically add normalization

        Returns:
            Created normalization rule if added
        """
        # Record failed recognition for the correct term
        self.record_usage(correct, success=False)

        if auto_add_rule:
            pattern = self.suggest_normalization(misheard, correct)
            rule = NormalizationRule(
                pattern=pattern,
                replacement=correct,
                custom=True,
            )
            self._normalizations.append(rule)

            if self.auto_save:
                self._save()

            return rule

        return None

    def reset_statistics(self) -> None:
        """Reset usage statistics (keep terms and rules)."""
        for term in self._terms.values():
            term.use_count = 0
            term.success_count = 0
            term.last_used = None

        for rule in self._normalizations:
            rule.use_count = 0
            rule.success_count = 0

        if self.auto_save:
            self._save()

    def clear_custom(self) -> None:
        """Remove all custom terms and rules."""
        self._terms = {
            k: v for k, v in self._terms.items()
            if not v.custom
        }
        self._normalizations = [
            r for r in self._normalizations
            if not r.custom
        ]

        if self.auto_save:
            self._save()


# =============================================================================
# Module-level singleton
# =============================================================================

_trainer: Optional[VocabularyTrainer] = None


def get_vocabulary_trainer() -> VocabularyTrainer:
    """Get the global vocabulary trainer instance."""
    global _trainer
    if _trainer is None:
        _trainer = VocabularyTrainer()
    return _trainer
