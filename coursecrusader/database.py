"""
SQLite database support for Course Crusader.

Provides easy export and querying of course data via SQLite.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from .models import Course


class CourseDatabase:
    """
    SQLite database interface for course catalog data.

    Provides convenient methods for storing and querying courses.
    """

    def __init__(self, db_path: str = "courses.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                country TEXT DEFAULT 'US',
                created_at TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT NOT NULL,
                course_id TEXT,
                url TEXT NOT NULL,
                kind TEXT DEFAULT 'catalog',
                last_seen TEXT,
                UNIQUE(university, url)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT NOT NULL,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                credits TEXT,
                level TEXT,
                department TEXT,
                prerequisites_text TEXT,
                prerequisites_json TEXT,  -- Stored as JSON string
                prerequisites_parsed BOOLEAN,
                corequisites_json TEXT,  -- Stored as JSON string
                restrictions TEXT,
                offerings_json TEXT,  -- Stored as JSON string
                catalog_url TEXT,
                last_updated TEXT,
                notes TEXT,
                UNIQUE(university, course_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_university
            ON courses(university)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_course_id
            ON courses(course_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_department
            ON courses(department)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_level
            ON courses(level)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT NOT NULL,
                scrape_date TEXT NOT NULL,
                courses_added INTEGER,
                courses_updated INTEGER,
                courses_removed INTEGER,
                scraper_version TEXT,
                notes TEXT
            )
        """)

        self.conn.commit()


    def upsert_institution(self, slug: str, name: str, country: str = "US") -> int:
        """Ensure an institution row exists; return its id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO institutions (slug, name, country, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET name=excluded.name
            """,
            (slug, name, country, datetime.utcnow().isoformat() + "Z"),
        )
        self.conn.commit()
        cursor.execute("SELECT id FROM institutions WHERE slug = ?", (slug,))
        return int(cursor.fetchone()[0])

    def record_source_url(
        self, university: str, url: str, course_id: str = None, kind: str = "catalog"
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO source_urls (university, course_id, url, kind, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(university, url) DO UPDATE SET
                course_id=excluded.course_id,
                kind=excluded.kind,
                last_seen=excluded.last_seen
            """,
            (university, course_id, url, kind, datetime.utcnow().isoformat() + "Z"),
        )
        self.conn.commit()

    def insert_course(self, course: Course) -> Dict[str, Any]:
        """
        Insert or update a course.

        Returns:
            Dict with row_id, added (0|1), updated (0|1).
        """
        cursor = self.conn.cursor()

        prerequisites_json = json.dumps(course.prerequisites) if course.prerequisites else None
        corequisites_json = json.dumps(course.corequisites) if course.corequisites else None
        offerings_json = json.dumps(course.offerings) if course.offerings else None

        existing = self.get_course(course.university, course.course_id)
        cursor.execute(
            """
            INSERT INTO courses (
                university, course_id, title, description, credits, level,
                department, prerequisites_text, prerequisites_json,
                prerequisites_parsed, corequisites_json, restrictions,
                offerings_json, catalog_url, last_updated, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(university, course_id) DO UPDATE SET
                title=excluded.title,
                description=excluded.description,
                credits=excluded.credits,
                level=excluded.level,
                department=excluded.department,
                prerequisites_text=excluded.prerequisites_text,
                prerequisites_json=excluded.prerequisites_json,
                prerequisites_parsed=excluded.prerequisites_parsed,
                corequisites_json=excluded.corequisites_json,
                restrictions=excluded.restrictions,
                offerings_json=excluded.offerings_json,
                catalog_url=excluded.catalog_url,
                last_updated=excluded.last_updated,
                notes=excluded.notes
        """,
            (
                course.university,
                course.course_id,
                course.title,
                course.description,
                str(course.credits),
                course.level,
                course.department,
                course.prerequisites_text,
                prerequisites_json,
                course.prerequisites_parsed,
                corequisites_json,
                course.restrictions,
                offerings_json,
                course.catalog_url,
                course.last_updated,
                course.notes,
            ),
        )

        self.conn.commit()
        row = self.get_course(course.university, course.course_id)
        row_id = row["id"] if row else cursor.lastrowid
        if existing:
            return {"row_id": row_id, "added": 0, "updated": 1}
        return {"row_id": row_id, "added": 1, "updated": 0}

    def insert_courses_bulk(self, courses: List[Course]) -> Dict[str, int]:
        """
        Insert multiple courses in one transaction.

        Returns:
            {"added": n, "updated": m}
        """
        added = 0
        updated = 0
        try:
            for course in courses:
                result = self.insert_course(course)
                added += result["added"]
                updated += result["updated"]
            return {"added": added, "updated": updated}
        except Exception:
            self.conn.rollback()
            raise

    def get_course(self, university: str, course_id: str) -> Optional[Dict]:
        """
        Get a single course by university and course ID.

        Args:
            university: University name
            course_id: Course identifier

        Returns:
            Course as dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM courses
            WHERE university = ? AND course_id = ?
        """,
            (university, course_id),
        )

        row = cursor.fetchone()
        return dict(row) if row else None

    def get_courses_by_university(self, university: str) -> List[Dict]:
        """
        Get all courses for a university.

        Args:
            university: University name

        Returns:
            List of course dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM courses
            WHERE university = ?
            ORDER BY course_id
        """,
            (university,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_courses_by_department(self, university: str, department: str) -> List[Dict]:
        """
        Get courses by department.

        Args:
            university: University name
            department: Department name

        Returns:
            List of course dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM courses
            WHERE university = ? AND department = ?
            ORDER BY course_id
        """,
            (university, department),
        )

        return [dict(row) for row in cursor.fetchall()]

    def search_courses(
        self,
        query: str,
        university: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search courses by title or description with pagination.

        Returns:
            {"rows": [...], "total": int, "truncated": bool}
        """
        cursor = self.conn.cursor()
        q = (query or "").strip()
        if not q:
            return {"rows": [], "total": 0, "truncated": False}

        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        like = f"%{q}%"

        if university:
            count_sql = """
                SELECT COUNT(*) FROM courses
                WHERE university = ?
                AND (title LIKE ? OR description LIKE ?)
            """
            count_args = (university, like, like)
            data_sql = """
                SELECT * FROM courses
                WHERE university = ?
                AND (title LIKE ? OR description LIKE ?)
                ORDER BY course_id
                LIMIT ? OFFSET ?
            """
            data_args = (university, like, like, limit, offset)
        else:
            count_sql = """
                SELECT COUNT(*) FROM courses
                WHERE title LIKE ? OR description LIKE ?
            """
            count_args = (like, like)
            data_sql = """
                SELECT * FROM courses
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY university, course_id
                LIMIT ? OFFSET ?
            """
            data_args = (like, like, limit, offset)

        cursor.execute(count_sql, count_args)
        total = cursor.fetchone()[0]
        cursor.execute(data_sql, data_args)
        rows = [dict(row) for row in cursor.fetchall()]
        return {
            "rows": rows,
            "total": total,
            "truncated": total > offset + len(rows),
        }

    VALID_OFFERINGS = ("Fall", "Spring", "Summer", "Winter", "Year-round")

    def courses_with_corequisite(
        self,
        course_id: str,
        university: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return courses whose corequisites_json list contains ``course_id``.

        Matching is exact against JSON array elements (not free-text description).
        Invalid JSON rows are skipped and counted in ``skipped_invalid``.
        """
        needle = (course_id or "").strip()
        if not needle:
            return {"rows": [], "skipped_invalid": 0}

        cursor = self.conn.cursor()
        if university:
            cursor.execute(
                """
                SELECT * FROM courses
                WHERE university = ?
                  AND corequisites_json IS NOT NULL
                  AND TRIM(corequisites_json) != ''
                ORDER BY course_id
                """,
                (university,),
            )
        else:
            cursor.execute("""
                SELECT * FROM courses
                WHERE corequisites_json IS NOT NULL
                  AND TRIM(corequisites_json) != ''
                ORDER BY university, course_id
                """)

        rows = []
        skipped_invalid = 0
        for row in cursor.fetchall():
            course = dict(row)
            raw = course.get("corequisites_json")
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, json.JSONDecodeError):
                skipped_invalid += 1
                continue
            if not isinstance(parsed, list):
                skipped_invalid += 1
                continue
            codes = {str(item).strip() for item in parsed if item is not None}
            if needle in codes:
                rows.append(course)
        return {"rows": rows, "skipped_invalid": skipped_invalid}

    def courses_offered_in(self, term: str) -> Dict[str, Any]:
        """Return courses whose offerings_json contains the exact term enum.

        ``Fall`` does not match ``Year-round``. Invalid JSON is skipped.
        """
        term_norm = (term or "").strip()
        if term_norm not in self.VALID_OFFERINGS:
            raise ValueError(f"Invalid term {term!r}; expected one of {list(self.VALID_OFFERINGS)}")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM courses
            WHERE offerings_json IS NOT NULL
              AND TRIM(offerings_json) != ''
            ORDER BY university, course_id
            """)

        rows = []
        skipped_invalid = 0
        for row in cursor.fetchall():
            course = dict(row)
            raw = course.get("offerings_json")
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, json.JSONDecodeError):
                skipped_invalid += 1
                continue
            if not isinstance(parsed, list):
                skipped_invalid += 1
                continue
            offerings = {str(item).strip() for item in parsed if item is not None}
            if term_norm in offerings:
                rows.append(course)
        return {"rows": rows, "skipped_invalid": skipped_invalid}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with statistics (total courses, by university, etc.)
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM courses")
        total_courses = cursor.fetchone()[0]

        cursor.execute("""
            SELECT university, COUNT(*) as count
            FROM courses
            GROUP BY university
            ORDER BY count DESC
        """)
        by_university = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT level, COUNT(*) as count
            FROM courses
            GROUP BY level
        """)
        by_level = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT
                COUNT(CASE WHEN prerequisites_parsed = 1 THEN 1 END) as parsed,
                COUNT(CASE WHEN prerequisites_text IS NOT NULL THEN 1 END) as total
            FROM courses
        """)
        prereq_row = cursor.fetchone()
        prereq_parse_rate = (prereq_row[0] / prereq_row[1] * 100) if prereq_row[1] > 0 else 0

        return {
            "total_courses": total_courses,
            "by_university": by_university,
            "by_level": by_level,
            "prerequisite_parse_rate": round(prereq_parse_rate, 2),
        }

    def record_scrape(
        self,
        university: str,
        courses_added: int,
        courses_updated: int = 0,
        courses_removed: int = 0,
        scraper_version: str = "0.1.0",
        notes: str = "",
    ):
        """
        Record metadata about a scraping run.

        Args:
            university: University scraped
            courses_added: Number of courses added
            courses_updated: Number of courses updated
            courses_removed: Number of courses removed
            scraper_version: Version of scraper used
            notes: Additional notes
        """
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO scrape_metadata (
                university, scrape_date, courses_added, courses_updated,
                courses_removed, scraper_version, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                university,
                datetime.utcnow().isoformat(),
                courses_added,
                courses_updated,
                courses_removed,
                scraper_version,
                notes,
            ),
        )

        self.conn.commit()

    def export_to_json(self, output_path: str, university: Optional[str] = None):
        """
        Export database to JSON file.

        Args:
            output_path: Path for output JSON file
            university: Optional university filter
        """
        if university:
            courses = self.get_courses_by_university(university)
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM courses ORDER BY university, course_id")
            courses = [dict(row) for row in cursor.fetchall()]

        for course in courses:
            if course.get("prerequisites_json"):
                course["prerequisites"] = json.loads(course["prerequisites_json"])
            if course.get("corequisites_json"):
                course["corequisites"] = json.loads(course["corequisites_json"])
            if course.get("offerings_json"):
                course["offerings"] = json.loads(course["offerings_json"])

            course.pop("prerequisites_json", None)
            course.pop("corequisites_json", None)
            course.pop("offerings_json", None)
            course.pop("id", None)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)

    def export_to_parquet(
        self,
        output_path: str,
        university: Optional[str] = None,
        partition_by_university: bool = False,
    ) -> int:
        """
        Export courses to Parquet for lakehouse / Data-visualizer handoff (#11).

        Returns number of rows written. Requires ``pyarrow``.
        When ``partition_by_university`` is True, writes a directory of
        ``university=<name>/part-0.parquet`` datasets.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "export --format parquet requires pyarrow; pip install pyarrow"
            ) from e

        if university:
            courses = self.get_courses_by_university(university)
        else:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM courses ORDER BY university, course_id")
            courses = [dict(row) for row in cursor.fetchall()]

        rows = []
        for course in courses:
            row = dict(course)
            row.pop("id", None)
            # Keep JSON columns as strings for stable schema; decode optional
            rows.append(row)

        if not rows:
            # Write empty table with known columns
            schema = pa.schema(
                [
                    ("university", pa.string()),
                    ("course_id", pa.string()),
                    ("title", pa.string()),
                    ("description", pa.string()),
                    ("credits", pa.string()),
                    ("level", pa.string()),
                    ("department", pa.string()),
                    ("prerequisites_text", pa.string()),
                    ("prerequisites_json", pa.string()),
                    ("prerequisites_parsed", pa.bool_()),
                    ("corequisites_json", pa.string()),
                    ("restrictions", pa.string()),
                    ("offerings_json", pa.string()),
                    ("catalog_url", pa.string()),
                    ("last_updated", pa.string()),
                    ("notes", pa.string()),
                ]
            )
            table = pa.Table.from_pylist([], schema=schema)
        else:
            table = pa.Table.from_pylist(rows)

        out = Path(output_path)
        if partition_by_university and not university:
            out.mkdir(parents=True, exist_ok=True)
            pq.write_to_dataset(
                table,
                root_path=str(out),
                partition_cols=["university"],
                existing_data_behavior="overwrite_or_ignore",
            )
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, str(out))
        return table.num_rows

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def import_jsonl_to_db(jsonl_path: str, db_path: str = "courses.db") -> int:
    """
    Import JSONL file into SQLite database.

    Args:
        jsonl_path: Path to JSONL file
        db_path: Path to database file

    Returns:
        Number of courses imported
    """
    db = CourseDatabase(db_path)
    count = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                course_data = json.loads(line)
                course = Course(**course_data)
                db.insert_course(course)
                count += 1

    db.close()
    return count
