import scrapy
from ..base import BaseCourseScraper
from ..registry import register_scraper


@register_scraper
class RochesterScraper(BaseCourseScraper):
    name = "rochester"
    university = "University of Rochester"
    start_urls = ['https://httpbin.org/html']

    custom_settings = {
        'FEEDS': {
            'rochester_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        self.logger.info(f"Demo scraper for {self.university}")
        sample_courses = [
            ("INTRO 101", "Introduction to Rochester", "Foundational course", 3),
            ("ADV 201", "Advanced Studies", "Upper-level coursework", 4),
            ("RES 301", "Research Methods", "Research methodology", 3),
        ]
        for code, title, desc, credits in sample_courses:
            course = self.create_course(
                course_id=code,
                title=title,
                description=desc,
                credits=credits,
                level=self.infer_level(code),
                department=code.split()[0],
                catalog_url=response.url
            )
            self.log_parse_success(course)
            yield course
            self.stats['courses_scraped'] += 1
