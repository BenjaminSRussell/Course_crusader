import scrapy
import re
from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class PennStateScraper(BaseCourseScraper):
    name = "penn_state"
    university = "Pennsylvania State University"
    start_urls = ['https://bulletins.psu.edu/university-course-descriptions/']

    custom_settings = {
        'FEEDS': {
            'penn_state_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS': 2,
    }

    def parse(self, response):
        self.logger.info(f"Parsing course listing page: {response.url}")
        dept_links = response.css('a::attr(href)').re(r'/courses/[a-z]+/')
        dept_links = list(set(dept_links))
        self.logger.info(f"Found {len(dept_links)} department links")
        for link in dept_links[:20]:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        self.logger.info(f"Parsing department page: {response.url}")
        dept_name = self._extract_department_name(response)
        course_blocks = response.css('div.courseblock')
        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")
        for block in course_blocks:
            try:
                course = self._parse_course_block(block, dept_name, response.url)
                if course:
                    self.log_parse_success(course)
                    yield course
                    self.stats['courses_scraped'] += 1
            except Exception as e:
                self.log_parse_failure(response.url, str(e))

    def _extract_department_name(self, response) -> str:
        title = response.css('h1::text').get()
        if title:
            title = re.sub(r'\s*\([A-Z]+\)\s*', '', title)
            return title.strip()
        match = re.search(r'/courses/([a-z]+)/', response.url)
        if match:
            return match.group(1).upper()
        return "Unknown"

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        code_elem = block.css('.detail-code::text, .courseblocktitle strong::text').get()
        title_elem = block.css('.detail-title::text, .courseblocktitle::text').get()
        credits_elem = block.css('.detail-hours_html::text, .courseblockhours::text').get()
        if not code_elem or not title_elem:
            return None
        course_id = clean_text(code_elem).rstrip('.').split('.')[0]
        course_title = clean_text(title_elem).rstrip('.')
        credits = extract_credits(credits_elem) if credits_elem else "Unknown"
        desc_elem = block.css('.courseblockextra::text, .courseblockdesc::text').get()
        description = clean_text(desc_elem) if desc_elem else ""
        prereq_data = {'prerequisites': None, 'prerequisites_text': None, 'prerequisites_parsed': True}
        level = self.infer_level(course_id)
        return self.create_course(
            course_id=course_id,
            title=course_title,
            description=description.strip(),
            credits=credits,
            level=level,
            department=dept_name,
            catalog_url=page_url,
            **prereq_data
        )
