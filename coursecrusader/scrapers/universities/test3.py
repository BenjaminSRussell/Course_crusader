import scrapy
from ..base import BaseCourseScraper
from ..registry import register_scraper

@register_scraper
class Test3Scraper(BaseCourseScraper):
    name = "test3"
    university = "Demo University Gamma"
    start_urls = ['https://httpbin.org/html']

    def parse(self, response):
        courses = [
            ("MATH 201", "Calculus II", "Integration and series", 4, "MATH 101"),
            ("CS 201", "Data Structures", "Lists, trees, graphs", 3, "CS 101"),
            ("PHYS 202", "Physics II", "Electricity and magnetism", 4, "PHYS 201 and MATH 101"),
            ("ENGL 301", "Technical Writing", "Writing for STEM fields", 3, "ENGL 201"),
            ("CS 301", "Algorithms", "Algorithm design and analysis", 3, "CS 201 and MATH 201"),
        ]
        for code, title, desc, credits, prereqs in courses:
            prereq_data = self.parse_prerequisites(prereqs)
            course = self.create_course(
                course_id=code,
                title=title,
                description=desc,
                credits=credits,
                level=self.infer_level(code),
                department=code.split()[0],
                catalog_url=response.url,
                **prereq_data
            )
            self.log_parse_success(course)
            yield course
            self.stats['courses_scraped'] += 1
