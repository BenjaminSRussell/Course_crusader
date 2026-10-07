import scrapy
from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class TestScraper(BaseCourseScraper):
    name = "test"
    university = "Test University"
    start_urls = ['https://httpbin.org/html']

    custom_settings = {
        'FEEDS': {
            'test_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        self.logger.info(f"Test scraper running on {response.url}")
        course = self.create_course(
            course_id="TEST 101",
            title="Introduction to Testing",
            description="A test course to verify the scraper framework works",
            credits=3,
            level="Undergraduate",
            department="Testing",
            catalog_url=response.url
        )
        self.log_parse_success(course)
        yield course
        self.stats['courses_scraped'] += 1
