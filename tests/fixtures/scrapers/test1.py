import scrapy
from ..base import BaseCourseScraper
from ..registry import register_scraper

@register_scraper
class Test1Scraper(BaseCourseScraper):
    name = "test1"
    university = "Demo University Alpha"
    start_urls = ['https://httpbin.org/html']

    def parse(self, response):
        courses = [
            ("MATH 101", "Calculus I", "Introduction to differential calculus", 4),
            ("CS 101", "Introduction to Programming", "Learn Python programming", 3),
            ("PHYS 201", "Physics I", "Mechanics and thermodynamics", 4),
        ]
        for code, title, desc, credits in courses:
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
