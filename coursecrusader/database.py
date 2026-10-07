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
            CREATE TABLE IF NOT EXISTS catalog_snapshots (
                university TEXT NOT NULL,
                url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                etag TEXT,
                fetched_at TEXT NOT NULL,
                course_count INTEGER DEFAULT 0,
                PRIMARY KEY (university, url)
            )
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


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                university TEXT NOT NULL,
                from_course_id TEXT NOT NULL,
                to_course_id TEXT NOT NULL,
                edge_type TEXT NOT NULL DEFAULT 'prerequisite',
                UNIQUE(university, from_course_id, to_course_id, edge_type)
            )
        """)

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS courses_fts USING fts5(
                university,
                course_id,
                title,
                description,
                department
            )
        """)

        # Backfill FTS if empty but courses exist
        cursor.execute("SELECT COUNT(*) FROM courses_fts")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO courses_fts(rowid, university, course_id, title, description, department)
                SELECT id, university, course_id, title, description, department FROM courses
                """
            )

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


    def get_catalog_snapshot(self, university: str, url: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM catalog_snapshots WHERE university = ? AND url = ?",
            (university, url),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def upsert_catalog_snapshot(
        self,
        university: str,
        url: str,
        content_hash: str,
        etag: str = None,
        course_count: int = 0,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO catalog_snapshots
                (university, url, content_hash, etag, fetched_at, course_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(university, url) DO UPDATE SET
                content_hash=excluded.content_hash,
                etag=excluded.etag,
                fetched_at=excluded.fetched_at,
                course_count=excluded.course_count
            """,
            (
                university,
                url,
                content_hash,
                etag,
                datetime.utcnow().isoformat() + "Z",
                course_count,
            ),
        )
        self.conn.commit()

    def refresh_courses_from_dicts(
        self, university: str, courses: list, content_hash: str, url: str = ""
    ) -> dict:
        """
        Upsert course dicts if snapshot hash changed; skip when unchanged (#6).

        ``courses`` items are kwargs for Course / insert_course.
        """
        from .models import Course

        url = url or f"snapshot://{university}"
        prev = self.get_catalog_snapshot(university, url)
        if prev and prev.get("content_hash") == content_hash:
            return {
                "skipped": True,
                "reason": "unchanged",
                "added": 0,
                "updated": 0,
                "total": prev.get("course_count") or 0,
            }

        added = updated = 0
        for raw in courses:
            data = dict(raw)
            data.setdefault("university", university)
            course = raw if isinstance(raw, Course) else Course(**data)
            result = self.insert_course(course)
            added += int(result.get("added", 0))
            updated += int(result.get("updated", 0))

        self.upsert_catalog_snapshot(
            university, url, content_hash, course_count=len(courses)
        )
        return {
            "skipped": False,
            "added": added,
            "updated": updated,
            "total": len(courses),
        }

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
        if row_id:
            cursor.execute("DELETE FROM courses_fts WHERE rowid = ?", (row_id,))
            cursor.execute(
                """
                INSERT INTO courses_fts(rowid, university, course_id, title, description, department)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    course.university,
                    course.course_id,
                    course.title,
                    course.description,
                    course.department,
                ),
            )
            self.conn.commit()
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
        Ranked search via FTS5 (falls back to LIKE if FTS unavailable).

        Returns:
            {"rows": [...], "total": int, "truncated": bool, "engine": "fts5"|"like"}
        """
        cursor = self.conn.cursor()
        q = (query or "").strip()
        if not q:
            return {"rows": [], "total": 0, "truncated": False, "engine": "fts5"}

        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))

        # FTS5 query: quote tokens for phrase-ish matching
        tokens = [tok for tok in q.replace('"', " ").split() if tok]
        fts_q = " ".join(f'"{t}"' for t in tokens) if tokens else q

        try:
            if university:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM courses_fts
                    WHERE courses_fts MATCH ? AND university = ?
                    """,
                    (fts_q, university),
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT c.* FROM courses c
                    JOIN courses_fts f ON c.id = f.rowid
                    WHERE courses_fts MATCH ? AND c.university = ?
                    ORDER BY bm25(courses_fts)
                    LIMIT ? OFFSET ?
                    """,
                    (fts_q, university, limit, offset),
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM courses_fts WHERE courses_fts MATCH ?",
                    (fts_q,),
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT c.* FROM courses c
                    JOIN courses_fts f ON c.id = f.rowid
                    WHERE courses_fts MATCH ?
                    ORDER BY bm25(courses_fts)
                    LIMIT ? OFFSET ?
                    """,
                    (fts_q, limit, offset),
                )
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "rows": rows,
                "total": total,
                "truncated": total > offset + len(rows),
                "engine": "fts5",
            }
        except Exception:
            # Fallback LIKE
            like = f"%{q}%"
            if university:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM courses
                    WHERE university = ?
                    AND (title LIKE ? OR description LIKE ? OR department LIKE ?)
                    """,
                    (university, like, like, like),
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT * FROM courses
                    WHERE university = ?
                    AND (title LIKE ? OR description LIKE ? OR department LIKE ?)
                    ORDER BY course_id
                    LIMIT ? OFFSET ?
                    """,
                    (university, like, like, like, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM courses
                    WHERE title LIKE ? OR description LIKE ? OR department LIKE ?
                    """,
                    (like, like, like),
                )
                total = cursor.fetchone()[0]
                cursor.execute(
                    """
                    SELECT * FROM courses
                    WHERE title LIKE ? OR description LIKE ? OR department LIKE ?
                    ORDER BY university, course_id
                    LIMIT ? OFFSET ?
                    """,
                    (like, like, like, limit, offset),
                )
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "rows": rows,
                "total": total,
                "truncated": total > offset + len(rows),
                "engine": "like",
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


    def rebuild_prerequisite_edges(self, university: Optional[str] = None) -> Dict[str, Any]:
        """Derive course_edges from prerequisites_json (#5). Returns counts + cycles."""
        cursor = self.conn.cursor()
        if university:
            cursor.execute("DELETE FROM course_edges WHERE university = ?", (university,))
            cursor.execute(
                "SELECT university, course_id, prerequisites_json FROM courses WHERE university = ?",
                (university,),
            )
        else:
            cursor.execute("DELETE FROM course_edges")
            cursor.execute("SELECT university, course_id, prerequisites_json FROM courses")

        rows = cursor.fetchall()
        inserted = 0
        for uni, cid, raw in rows:
            if not raw:
                continue
            try:
                tree = json.loads(raw)
            except Exception:
                continue
            for prereq in self._flatten_prereq_codes(tree):
                if not prereq or prereq == cid:
                    continue
                try:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO course_edges
                            (university, from_course_id, to_course_id, edge_type)
                        VALUES (?, ?, ?, 'prerequisite')
                        """,
                        (uni, prereq, cid),
                    )
                    inserted += cursor.rowcount
                except Exception:
                    pass
        self.conn.commit()
        cycles = self.detect_edge_cycles(university)
        return {"edges": inserted, "cycles": cycles}

    @staticmethod
    def _flatten_prereq_codes(node) -> List[str]:
        """Walk and/or trees or flat lists into course code strings."""
        out: List[str] = []
        if node is None:
            return out
        if isinstance(node, str):
            return [node.strip()] if node.strip() else []
        if isinstance(node, list):
            for item in node:
                out.extend(CourseDatabase._flatten_prereq_codes(item))
            return out
        if isinstance(node, dict):
            for key in ("and", "or", "courses", "all_of", "any_of"):
                if key in node:
                    out.extend(CourseDatabase._flatten_prereq_codes(node[key]))
            # bare {"course": "CSE 1010"} style
            if "course" in node and isinstance(node["course"], str):
                out.append(node["course"].strip())
            return out
        return out

    def detect_edge_cycles(self, university: Optional[str] = None) -> List[List[str]]:
        """Return list of cycles (each a list of course_ids) via DFS."""
        cursor = self.conn.cursor()
        if university:
            cursor.execute(
                "SELECT from_course_id, to_course_id FROM course_edges WHERE university = ?",
                (university,),
            )
        else:
            cursor.execute("SELECT from_course_id, to_course_id FROM course_edges")
        graph: Dict[str, List[str]] = {}
        for frm, to in cursor.fetchall():
            graph.setdefault(frm, []).append(to)

        cycles: List[List[str]] = []
        visited = set()
        stack = []
        onstack = set()

        def dfs(node: str):
            visited.add(node)
            onstack.add(node)
            stack.append(node)
            for nxt in graph.get(node, []):
                if nxt not in visited:
                    dfs(nxt)
                elif nxt in onstack:
                    if nxt in stack:
                        i = stack.index(nxt)
                        cycles.append(stack[i:] + [nxt])
            stack.pop()
            onstack.discard(node)

        for n in list(graph.keys()):
            if n not in visited:
                dfs(n)
        return cycles

    def export_graph(
        self, course_id: str, university: Optional[str] = None, fmt: str = "json"
    ) -> str:
        """Export prerequisite paths into ``course_id`` as JSON or DOT (#5)."""
        cursor = self.conn.cursor()
        if university:
            cursor.execute(
                """
                SELECT from_course_id, to_course_id, edge_type, university
                FROM course_edges
                WHERE university = ?
                """,
                (university,),
            )
        else:
            cursor.execute(
                "SELECT from_course_id, to_course_id, edge_type, university FROM course_edges"
            )
        edges = [dict(row) for row in cursor.fetchall()]
        # Filter to ancestors of course_id
        target = course_id.strip()
        reverse: Dict[str, List[str]] = {}
        for e in edges:
            reverse.setdefault(e["to_course_id"], []).append(e["from_course_id"])
        keep = set()
        stack = [target]
        while stack:
            n = stack.pop()
            if n in keep:
                continue
            keep.add(n)
            for p in reverse.get(n, []):
                stack.append(p)
        filtered = [
            e
            for e in edges
            if e["from_course_id"] in keep and e["to_course_id"] in keep
        ]
        if fmt == "dot":
            lines = ["digraph prereqs {"]
            for e in filtered:
                lines.append(
                    f'  "{e["from_course_id"]}" -> "{e["to_course_id"]}" '
                    f'[label="{e["edge_type"]}"];'
                )
            lines.append("}")
            return "\n".join(lines)
        return json.dumps({"course_id": target, "edges": filtered}, indent=2)

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
