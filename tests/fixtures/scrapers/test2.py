import scrapy
from ..base import BaseCourseScraper
from ..registry import register_scraper

@register_scraper
class Test2Scraper(BaseCourseScraper):
    name = "test2"
    university = "Demo University Beta"
    start_urls = ['https://httpbin.org/html']

    def parse(self, response):
        courses = [
            ("CHEM 101", "General Chemistry", "Atomic structure and bonding", 4),
            ("BIOL 101", "Biology I", "Cell biology and genetics", 4),
            ("ENGL 201", "English Composition", "Advanced writing skills", 3),
            ("HIST 101", "World History", "Survey of world civilizations", 3),
        ]
        for code, title, desc, credits in courses:
            course = self.create_course(
                course_id=code,
                title=title,
                description=desc,
                credits=credits,
                level=self.infer_level(code),
                department=code.split()[0],
                catalog_url=response.url,
                prerequisites_text="None"
            )
            self.log_parse_success(course)
            yield course
            self.stats['courses_scraped'] += 1
