"""
Scrapy item pipelines for Course Crusader.

Pipelines process scraped courses for validation, deduplication, etc.
"""

from typing import Set
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from .models import Course


class ValidationPipeline:
    """
    Validate course items before saving.

    Ensures all courses conform to the schema and have required fields.
    """

    def process_item(self, item, spider):
        """Validate a course item."""
        adapter = ItemAdapter(item)

        if isinstance(item, Course):
            is_valid, errors = item.validate()

            if not is_valid:
                spider.logger.warning(f"Validation failed for {item.course_id}: {errors}")
                if item.notes:
                    item.notes += f" | Validation warnings: {'; '.join(errors)}"
                else:
                    item.notes = f"Validation warnings: {'; '.join(errors)}"

            return item

        try:
            course = Course(**dict(adapter))
            is_valid, errors = course.validate()

            if not is_valid:
                spider.logger.warning(f"Validation failed for {course.course_id}: {errors}")
                course.notes = f"Validation warnings: {'; '.join(errors)}"

            return course

        except Exception as e:
            spider.logger.error(f"Failed to create Course object: {e}")
            raise DropItem(f"Invalid course data: {e}")


class DeduplicationPipeline:
    """
    Remove duplicate courses based on university + course_id.

    Keeps the first occurrence of each course.
    """

    def __init__(self):
        self.seen_courses: Set[tuple] = set()

    def process_item(self, item, spider):
        """Check for duplicates."""
        adapter = ItemAdapter(item)

        if isinstance(item, Course):
            key = (item.university, item.course_id)
        else:
            key = (adapter.get("university"), adapter.get("course_id"))

        if key in self.seen_courses:
            spider.logger.debug(f"Duplicate course dropped: {key[0]} {key[1]}")
            raise DropItem(f"Duplicate course: {key[0]} {key[1]}")

        self.seen_courses.add(key)
        return item


class JsonExportPipeline:
    """
    Export courses to JSON format.

    Converts Course objects to dictionaries for export.
    """

    def process_item(self, item, spider):
        """Convert Course to dict for JSON export."""
        if isinstance(item, Course):
            return item.to_dict()
        return item


class SqlitePipeline:
    """
    Persist Course items into CourseDatabase (#9).

    Enabled when COURSECRUSADER_DB_PATH is set (default: courses.db).
    Upserts by (university, course_id) and records scrape_metadata on close.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = None
        self.added = 0
        self.updated = 0
        self.errors = 0

    @classmethod
    def from_crawler(cls, crawler):
        path = crawler.settings.get("COURSECRUSADER_DB_PATH", "courses.db")
        return cls(db_path=path)

    def open_spider(self, spider):
        from .database import CourseDatabase

        self.db = CourseDatabase(self.db_path)
        spider.logger.info(f"SqlitePipeline writing to {self.db_path}")

    def close_spider(self, spider):
        if self.db is None:
            return
        university = getattr(spider, "university", spider.name)
        try:
            self.db.record_scrape(
                university=university,
                courses_added=self.added,
                courses_updated=self.updated,
                notes=f"errors={self.errors}",
            )
        finally:
            self.db.close()
            spider.logger.info(
                f"SqlitePipeline closed: +{self.added} ~{self.updated} !{self.errors}"
            )

    def process_item(self, item, spider):
        if self.db is None:
            return item
        course = item if isinstance(item, Course) else None
        if course is None:
            try:
                course = Course(**ItemAdapter(item).asdict())
            except Exception as e:
                self.errors += 1
                spider.logger.error(f"SqlitePipeline skip: {e}")
                return item
        try:
            result = self.db.insert_course(course)
            self.added += int(result.get("added", 0))
            self.updated += int(result.get("updated", 0))
        except Exception as e:
            self.errors += 1
            spider.logger.error(f"SqlitePipeline insert failed: {e}")
        return item
