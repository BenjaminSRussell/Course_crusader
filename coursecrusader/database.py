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

    def insert_course(self, course: Course) -> int:
        """
        Insert a course into the database.

        Args:
            course: Course object to insert

        Returns:
            Row ID of inserted course
        """
        cursor = self.conn.cursor()

        prerequisites_json = json.dumps(course.prerequisites) if course.prerequisites else None
        corequisites_json = json.dumps(course.corequisites) if course.corequisites else None
        offerings_json = json.dumps(course.offerings) if course.offerings else None

        cursor.execute("""
            INSERT OR REPLACE INTO courses (
                university, course_id, title, description, credits, level,
                department, prerequisites_text, prerequisites_json,
                prerequisites_parsed, corequisites_json, restrictions,
                offerings_json, catalog_url, last_updated, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
            course.notes
        ))

        self.conn.commit()
        return cursor.lastrowid

    def insert_courses_bulk(self, courses: List[Course]) -> int:
        """
        Insert multiple courses efficiently.

        Args:
            courses: List of Course objects

        Returns:
            Number of courses inserted
        """
        count = 0
        for course in courses:
            self.insert_course(course)
            count += 1

        return count

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
        cursor.execute("""
            SELECT * FROM courses
            WHERE university = ? AND course_id = ?
        """, (university, course_id))

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
        cursor.execute("""
            SELECT * FROM courses
            WHERE university = ?
            ORDER BY course_id
        """, (university,))

        return [dict(row) for row in cursor.fetchall()]

    def get_courses_by_department(
        self,
        university: str,
        department: str
    ) -> List[Dict]:
        """
        Get courses by department.

        Args:
            university: University name
            department: Department name

        Returns:
            List of course dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM courses
            WHERE university = ? AND department = ?
            ORDER BY course_id
        """, (university, department))

        return [dict(row) for row in cursor.fetchall()]

    def search_courses(
        self,
        query: str,
        university: Optional[str] = None
    ) -> List[Dict]:
        """
        Search courses by title or description.

        Args:
            query: Search query
            university: Optional university filter

        Returns:
            List of matching course dictionaries
        """
        cursor = self.conn.cursor()

        if university:
            cursor.execute("""
                SELECT * FROM courses
                WHERE university = ?
                AND (title LIKE ? OR description LIKE ?)
                ORDER BY course_id
            """, (university, f"%{query}%", f"%{query}%"))
        else:
            cursor.execute("""
                SELECT * FROM courses
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY university, course_id
            """, (f"%{query}%", f"%{query}%"))

        return [dict(row) for row in cursor.fetchall()]

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
            'total_courses': total_courses,
            'by_university': by_university,
            'by_level': by_level,
            'prerequisite_parse_rate': round(prereq_parse_rate, 2)
        }

    def record_scrape(
        self,
        university: str,
        courses_added: int,
        courses_updated: int = 0,
        courses_removed: int = 0,
        scraper_version: str = "0.1.0",
        notes: str = ""
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

        cursor.execute("""
            INSERT INTO scrape_metadata (
                university, scrape_date, courses_added, courses_updated,
                courses_removed, scraper_version, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            university,
            datetime.utcnow().isoformat(),
            courses_added,
            courses_updated,
            courses_removed,
            scraper_version,
            notes
        ))

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
            if course.get('prerequisites_json'):
                course['prerequisites'] = json.loads(course['prerequisites_json'])
            if course.get('corequisites_json'):
                course['corequisites'] = json.loads(course['corequisites_json'])
            if course.get('offerings_json'):
                course['offerings'] = json.loads(course['offerings_json'])

            course.pop('prerequisites_json', None)
            course.pop('corequisites_json', None)
            course.pop('offerings_json', None)
            course.pop('id', None)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)

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

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                course_data = json.loads(line)
                course = Course(**course_data)
                db.insert_course(course)
                count += 1

    db.close()
    return count
