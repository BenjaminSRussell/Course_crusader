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
                spider.logger.warning(
                    f"Validation failed for {item.course_id}: {errors}"
                )
                if item.notes:
                    item.notes += f" | Validation warnings: {'; '.join(errors)}"
                else:
                    item.notes = f"Validation warnings: {'; '.join(errors)}"

            return item

        try:
            course = Course(**dict(adapter))
            is_valid, errors = course.validate()

            if not is_valid:
                spider.logger.warning(
                    f"Validation failed for {course.course_id}: {errors}"
                )
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
            key = (adapter.get('university'), adapter.get('course_id'))

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
