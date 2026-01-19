"""
NIGHTWATCH Catalog Service
Astronomical Object Database

This module provides lookup services for astronomical objects including:
- Messier catalog (M1-M110)
- NGC catalog (NGC 1 - NGC 7840+)
- IC catalog (IC 1 - IC 5386)
- Named stars (Polaris, Vega, etc.)
- Planets (via ephemeris service)
- Common names (Orion Nebula, Ring Nebula, etc.)

Data stored in SQLite for fast local queries with voice control.
"""

import sqlite3
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple


class ObjectType(Enum):
    """Astronomical object types."""
    STAR = "star"
    DOUBLE_STAR = "double_star"
    VARIABLE_STAR = "variable_star"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    NEBULA = "nebula"
    PLANETARY_NEBULA = "planetary_nebula"
    GALAXY = "galaxy"
    GALAXY_CLUSTER = "galaxy_cluster"
    SUPERNOVA_REMNANT = "supernova_remnant"
    PLANET = "planet"
    ASTEROID = "asteroid"
    COMET = "comet"
    OTHER = "other"


@dataclass
class CatalogObject:
    """Astronomical object from catalog."""
    catalog_id: str           # e.g., "M31", "NGC 224", "IC 434"
    name: Optional[str]       # Common name, e.g., "Andromeda Galaxy"
    object_type: ObjectType
    ra_hours: float           # Right Ascension in decimal hours (J2000)
    dec_degrees: float        # Declination in decimal degrees (J2000)
    magnitude: Optional[float]
    size_arcmin: Optional[float]
    constellation: Optional[str]
    description: Optional[str]
    aliases: List[str]        # Alternative designations

    @property
    def ra_hms(self) -> str:
        """RA in HH:MM:SS format."""
        h = int(self.ra_hours)
        m = int((self.ra_hours - h) * 60)
        s = ((self.ra_hours - h) * 60 - m) * 60
        return f"{h:02d}:{m:02d}:{s:05.2f}"

    @property
    def dec_dms(self) -> str:
        """DEC in sDD:MM:SS format."""
        sign = "+" if self.dec_degrees >= 0 else "-"
        d = abs(self.dec_degrees)
        deg = int(d)
        m = int((d - deg) * 60)
        s = ((d - deg) * 60 - m) * 60
        return f"{sign}{deg:02d}:{m:02d}:{s:05.2f}"


class CatalogDatabase:
    """
    SQLite-based astronomical catalog database.

    Provides fast local queries for object lookup by various identifiers.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY,
        catalog_id TEXT UNIQUE NOT NULL,
        name TEXT,
        object_type TEXT NOT NULL,
        ra_hours REAL NOT NULL,
        dec_degrees REAL NOT NULL,
        magnitude REAL,
        size_arcmin REAL,
        constellation TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY,
        object_id INTEGER NOT NULL,
        alias TEXT NOT NULL,
        FOREIGN KEY (object_id) REFERENCES objects(id),
        UNIQUE(object_id, alias)
    );

    CREATE INDEX IF NOT EXISTS idx_catalog_id ON objects(catalog_id);
    CREATE INDEX IF NOT EXISTS idx_name ON objects(name);
    CREATE INDEX IF NOT EXISTS idx_alias ON aliases(alias);
    CREATE INDEX IF NOT EXISTS idx_constellation ON objects(constellation);
    CREATE INDEX IF NOT EXISTS idx_type ON objects(object_type);
    """

    def __init__(self, db_path: str = "nightwatch_catalog.db"):
        self.db_path = db_path
        self._conn = None

    def connect(self):
        """Connect to database and create schema if needed."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert_object(self, obj: CatalogObject):
        """Insert an object into the catalog."""
        cursor = self._conn.cursor()

        # Check if object already exists
        cursor.execute(
            "SELECT id FROM objects WHERE catalog_id = ?",
            (obj.catalog_id,)
        )
        existing = cursor.fetchone()

        if existing:
            object_id = existing[0]
            # Update existing object
            cursor.execute("""
                UPDATE objects SET
                    name = ?, object_type = ?, ra_hours = ?, dec_degrees = ?,
                    magnitude = ?, size_arcmin = ?, constellation = ?, description = ?
                WHERE id = ?
            """, (
                obj.name,
                obj.object_type.value,
                obj.ra_hours,
                obj.dec_degrees,
                obj.magnitude,
                obj.size_arcmin,
                obj.constellation,
                obj.description,
                object_id
            ))
        else:
            # Insert new object
            cursor.execute("""
                INSERT INTO objects
                (catalog_id, name, object_type, ra_hours, dec_degrees,
                 magnitude, size_arcmin, constellation, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obj.catalog_id,
                obj.name,
                obj.object_type.value,
                obj.ra_hours,
                obj.dec_degrees,
                obj.magnitude,
                obj.size_arcmin,
                obj.constellation,
                obj.description
            ))
            object_id = cursor.lastrowid

        # Insert aliases (ignore duplicates)
        for alias in obj.aliases:
            cursor.execute("""
                INSERT OR IGNORE INTO aliases (object_id, alias)
                VALUES (?, ?)
            """, (object_id, alias.upper()))

        self._conn.commit()

    def lookup(self, query: str) -> Optional[CatalogObject]:
        """
        Look up an object by catalog ID, name, or alias.

        Args:
            query: Search string (e.g., "M31", "Andromeda", "NGC 224")

        Returns:
            CatalogObject if found, None otherwise
        """
        query = query.strip().upper()
        cursor = self._conn.cursor()

        # Try exact catalog_id match
        cursor.execute("""
            SELECT * FROM objects WHERE UPPER(catalog_id) = ?
        """, (query,))
        row = cursor.fetchone()

        if not row:
            # Try name match
            cursor.execute("""
                SELECT * FROM objects WHERE UPPER(name) = ?
            """, (query,))
            row = cursor.fetchone()

        if not row:
            # Try alias match
            cursor.execute("""
                SELECT o.* FROM objects o
                JOIN aliases a ON o.id = a.object_id
                WHERE a.alias = ?
            """, (query,))
            row = cursor.fetchone()

        if not row:
            # Try partial name match
            cursor.execute("""
                SELECT * FROM objects WHERE UPPER(name) LIKE ?
                ORDER BY LENGTH(name) LIMIT 1
            """, (f"%{query}%",))
            row = cursor.fetchone()

        if row:
            return self._row_to_object(row)
        return None

    def search(
        self,
        query: Optional[str] = None,
        object_type: Optional[ObjectType] = None,
        constellation: Optional[str] = None,
        min_altitude: Optional[float] = None,
        max_magnitude: Optional[float] = None,
        limit: int = 50
    ) -> List[CatalogObject]:
        """
        Search catalog with filters.

        Args:
            query: Text search in name/description
            object_type: Filter by object type
            constellation: Filter by constellation
            min_altitude: Minimum altitude (requires ephemeris)
            max_magnitude: Maximum (brightest) magnitude
            limit: Maximum results to return

        Returns:
            List of matching CatalogObject
        """
        cursor = self._conn.cursor()

        sql = "SELECT * FROM objects WHERE 1=1"
        params = []

        if query:
            sql += " AND (UPPER(name) LIKE ? OR UPPER(description) LIKE ?)"
            params.extend([f"%{query.upper()}%", f"%{query.upper()}%"])

        if object_type:
            sql += " AND object_type = ?"
            params.append(object_type.value)

        if constellation:
            sql += " AND UPPER(constellation) = ?"
            params.append(constellation.upper())

        if max_magnitude is not None:
            sql += " AND magnitude <= ?"
            params.append(max_magnitude)

        sql += " ORDER BY magnitude LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_messier_catalog(self) -> List[CatalogObject]:
        """Get all Messier objects."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM objects WHERE catalog_id LIKE 'M%'
            ORDER BY CAST(SUBSTR(catalog_id, 2) AS INTEGER)
        """)
        return [self._row_to_object(row) for row in cursor.fetchall()]

    def _row_to_object(self, row: tuple) -> CatalogObject:
        """Convert database row to CatalogObject."""
        cursor = self._conn.cursor()

        # Get aliases
        cursor.execute("""
            SELECT alias FROM aliases WHERE object_id = ?
        """, (row[0],))
        aliases = [r[0] for r in cursor.fetchall()]

        return CatalogObject(
            catalog_id=row[1],
            name=row[2],
            object_type=ObjectType(row[3]),
            ra_hours=row[4],
            dec_degrees=row[5],
            magnitude=row[6],
            size_arcmin=row[7],
            constellation=row[8],
            description=row[9],
            aliases=aliases
        )

    def get_stats(self) -> dict:
        """Get catalog statistics."""
        cursor = self._conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM objects")
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT object_type, COUNT(*) FROM objects
            GROUP BY object_type
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        return {"total": total, "by_type": by_type}


# =============================================================================
# FUZZY MATCHING
# =============================================================================

def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _similarity_score(query: str, target: str) -> float:
    """Calculate similarity score (0-1) between query and target string."""
    query = query.upper()
    target = target.upper()

    # Exact match
    if query == target:
        return 1.0

    # Starts with bonus
    if target.startswith(query):
        return 0.95

    # Contains bonus
    if query in target:
        return 0.85

    # Levenshtein-based similarity
    max_len = max(len(query), len(target))
    if max_len == 0:
        return 0.0

    distance = _levenshtein_distance(query, target)
    return max(0.0, 1.0 - (distance / max_len))


# =============================================================================
# CATALOG DATA LOADERS
# =============================================================================

def load_messier_catalog(db: CatalogDatabase):
    """Load complete Messier catalog (M1-M110)."""
    try:
        from services.catalog.messier_data import get_messier_catalog
        messier = get_messier_catalog()
    except ImportError:
        messier = []

    for obj in messier:
        db.insert_object(obj)


def load_ngc_catalog(db: CatalogDatabase):
    """Load NGC catalog (popular objects)."""
    try:
        from services.catalog.catalog_data import get_ngc_catalog
        ngc = get_ngc_catalog()
    except ImportError:
        ngc = []

    for obj in ngc:
        db.insert_object(obj)


def load_ic_catalog(db: CatalogDatabase):
    """Load IC catalog (popular objects)."""
    try:
        from services.catalog.catalog_data import get_ic_catalog
        ic = get_ic_catalog()
    except ImportError:
        ic = []

    for obj in ic:
        db.insert_object(obj)


def load_named_stars(db: CatalogDatabase):
    """Load bright named stars."""
    try:
        from services.catalog.catalog_data import get_named_stars
        stars = get_named_stars()
    except ImportError:
        stars = []

    for star in stars:
        db.insert_object(star)


def load_double_stars(db: CatalogDatabase):
    """Load showpiece double stars."""
    try:
        from services.catalog.catalog_data import get_double_stars
        doubles = get_double_stars()
    except ImportError:
        doubles = []

    for double in doubles:
        db.insert_object(double)


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

class CatalogService:
    """
    High-level catalog service for NIGHTWATCH.

    Provides simple lookup interface for voice commands.
    """

    def __init__(self, db_path: str = "nightwatch_catalog.db"):
        self.db = CatalogDatabase(db_path)

    def initialize(self):
        """Initialize database with all catalog data."""
        self.db.connect()

        # Load catalogs if database is empty
        stats = self.db.get_stats()
        if stats["total"] == 0:
            load_messier_catalog(self.db)
            load_ngc_catalog(self.db)
            load_ic_catalog(self.db)
            load_named_stars(self.db)
            load_double_stars(self.db)

    def close(self):
        """Close database connection."""
        self.db.close()

    def lookup(self, query: str) -> Optional[CatalogObject]:
        """
        Look up an object by name or catalog ID.

        Examples:
            lookup("M31") -> Andromeda Galaxy
            lookup("Andromeda") -> Andromeda Galaxy
            lookup("Orion Nebula") -> M42
        """
        return self.db.lookup(query)

    def what_is(self, query: str) -> str:
        """
        Get a description of an object (for voice response).

        Returns:
            Human-readable description string
        """
        obj = self.lookup(query)
        if not obj:
            return f"I couldn't find {query} in the catalog."

        parts = [f"{obj.catalog_id}"]
        if obj.name:
            parts[0] = f"{obj.name} ({obj.catalog_id})"

        parts.append(f"is a {obj.object_type.value.replace('_', ' ')}")

        if obj.constellation:
            parts.append(f"in {obj.constellation}")

        if obj.magnitude:
            parts.append(f"with magnitude {obj.magnitude}")

        if obj.description:
            parts.append(f"- {obj.description}")

        return " ".join(parts)

    def get_coordinates(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Get coordinates for an object.

        Returns:
            Tuple of (RA in HH:MM:SS, DEC in sDD:MM:SS) or None
        """
        obj = self.lookup(query)
        if obj:
            return (obj.ra_hms, obj.dec_dms)
        return None

    def fuzzy_search(
        self,
        query: str,
        min_score: float = 0.6,
        limit: int = 10
    ) -> List[Tuple[CatalogObject, float]]:
        """
        Search for objects using fuzzy name matching.

        Useful for voice control where names may be misheard or
        partially spoken. Returns results sorted by match score.

        Args:
            query: Search string (can be partial or misspelled)
            min_score: Minimum similarity score (0-1) to include
            limit: Maximum results to return

        Returns:
            List of (CatalogObject, score) tuples sorted by score descending

        Examples:
            fuzzy_search("andromdea") -> [(Andromeda Galaxy, 0.91), ...]
            fuzzy_search("orion") -> [(Orion Nebula, 0.95), ...]
            fuzzy_search("betle") -> [(Betelgeuse, 0.75), ...]
        """
        cursor = self.db._conn.cursor()

        # Get all objects with names
        cursor.execute("SELECT * FROM objects WHERE name IS NOT NULL")
        rows = cursor.fetchall()

        results = []
        for row in rows:
            obj = self.db._row_to_object(row)
            if obj.name:
                score = _similarity_score(query, obj.name)
                if score >= min_score:
                    results.append((obj, score))

            # Also check aliases
            for alias in obj.aliases:
                alias_score = _similarity_score(query, alias)
                if alias_score >= min_score and alias_score > score:
                    results.append((obj, alias_score))
                    break

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def suggest(self, query: str, limit: int = 5) -> List[str]:
        """
        Get name suggestions for partial input (autocomplete).

        Useful for voice control confirmation.

        Args:
            query: Partial name input
            limit: Maximum suggestions

        Returns:
            List of suggested object names
        """
        results = self.fuzzy_search(query, min_score=0.5, limit=limit)
        suggestions = []
        for obj, score in results:
            if obj.name:
                suggestions.append(obj.name)
            else:
                suggestions.append(obj.catalog_id)
        return suggestions


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    service = CatalogService(":memory:")  # In-memory for testing
    service.initialize()

    # Get stats
    stats = service.db.get_stats()
    print(f"Catalog loaded: {stats['total']} objects")
    print(f"By type: {stats['by_type']}\n")

    # Test lookups
    print("Testing catalog lookups:\n")

    queries = ["M31", "Andromeda", "Orion Nebula", "Polaris", "M13", "Sirius",
               "NGC 7000", "Albireo", "Horsehead"]

    for q in queries:
        result = service.lookup(q)
        if result:
            print(f"{q:15} -> {result.catalog_id:8} {result.name or ''}")
            print(f"              RA: {result.ra_hms}  DEC: {result.dec_dms}")
        else:
            print(f"{q:15} -> Not found")
        print()

    # Test what_is
    print("\nVoice response test:")
    print(service.what_is("Ring Nebula"))

    # Test fuzzy search
    print("\n\nFuzzy search tests:")
    fuzzy_queries = ["andromdea", "orion", "betle", "pleiads", "horshead"]
    for q in fuzzy_queries:
        results = service.fuzzy_search(q, limit=3)
        print(f"\n'{q}' matches:")
        for obj, score in results:
            print(f"  {score:.2f} - {obj.name or obj.catalog_id}")

    # Test suggestions
    print("\n\nSuggestion tests:")
    for partial in ["and", "ori", "veg"]:
        suggestions = service.suggest(partial)
        print(f"'{partial}' -> {suggestions}")

    service.close()
