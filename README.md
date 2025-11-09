# Course Crusader

**Unified Course Catalog Scraper for Multiple Universities**

Course Crusader is a modular Python framework for scraping and normalizing university course catalogs into a unified JSON schema. It handles diverse catalog formats (HTML, PDF) and provides a simple CLI and API for easy integration.

## Features

### 🎯 Core Capabilities

- **Unified Schema**: All universities' data normalized to consistent JSON format
- **Multi-School Support**: Plug-in architecture for easy addition of new universities
- **High Data Quality**: Robust parsing with 90%+ course capture and accuracy goals
- **Prerequisite Parsing**: Intelligent extraction of course prerequisites into structured logic
- **PDF Support**: Handles both HTML and PDF-based course catalogs
- **Easy Integration**: CLI tool, Python API, and multiple export formats (JSONL, JSON, CSV)

### 🏫 Supported Universities

- **UConn** (University of Connecticut) - CourseLeaf-based catalog
- **MIT** (Massachusetts Institute of Technology) - Custom format
- **Yale** (Yale University) - Alternative catalog structure
- **Easily extensible** - Add new schools in hours, not weeks

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/BenjaminSRussell/Course_crusader.git
cd Course_crusader

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

```bash
# List available university scrapers
coursecrusader list

# Scrape UConn course catalog
coursecrusader scrape --school uconn

# Scrape MIT courses to JSON format
coursecrusader scrape --school mit --format json --output mit_courses.json

# Validate scraped data
coursecrusader validate uconn_courses.jsonl

# Merge multiple catalogs
coursecrusader merge uconn.jsonl mit.jsonl yale.jsonl -o combined.jsonl

# View the schema
coursecrusader schema

# NEW: Import to SQLite database
coursecrusader import-db uconn_courses.jsonl

# NEW: Database statistics
coursecrusader db-stats

# NEW: Search courses in database
coursecrusader search "machine learning" --university MIT
```

## Data Schema

Each course conforms to this unified schema:

```json
{
  "university": "University of Connecticut",
  "course_id": "CSE 2100",
  "title": "Data Structures and Introduction to Algorithms",
  "description": "Introduction to the design and analysis of fundamental data structures...",
  "credits": 3,
  "level": "Undergraduate",
  "department": "Computer Science & Engineering",
  "prerequisites": {
    "and": ["CSE 1010", {"or": ["MATH 2210Q", "MATH 2410Q"]}]
  },
  "prerequisites_text": "CSE 1010 and (MATH 2210Q or MATH 2410Q)",
  "prerequisites_parsed": true,
  "catalog_url": "https://catalog.uconn.edu/...",
  "last_updated": "2025-11-09T12:00:00Z"
}
```

### Required Fields

- `university`: Institution name
- `course_id`: Course code (e.g., "CSE 2100")
- `title`: Course title
- `description`: Full course description
- `credits`: Credit hours (number or string for ranges)
- `level`: "Undergraduate", "Graduate", "Professional", or "Unknown"
- `department`: Academic department

### Optional Fields

- `prerequisites`: Structured prerequisite logic (nested AND/OR)
- `prerequisites_text`: Original prerequisite text
- `prerequisites_parsed`: Boolean flag for parse confidence
- `corequisites`: List of concurrent courses
- `restrictions`: Enrollment restrictions
- `offerings`: Semesters when offered
- `catalog_url`: Source URL
- `last_updated`: ISO timestamp
- `notes`: Additional parsing notes

## Python API

Use Course Crusader programmatically in your Python code:

```python
from coursecrusader import Course
from coursecrusader.scrapers.registry import ScraperRegistry
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Get a scraper
UConnScraper = ScraperRegistry.get('uconn')

# Run it
settings = get_project_settings()
settings.set('FEEDS', {'courses.jsonl': {'format': 'jsonlines'}})

process = CrawlerProcess(settings)
process.crawl(UConnScraper)
process.start()

# Load and validate results
import json
from coursecrusader.models import Course

with open('courses.jsonl', 'r') as f:
    for line in f:
        course_data = json.loads(line)
        course = Course(**course_data)
        is_valid, errors = course.validate()
        if is_valid:
            print(f"✓ {course.course_id}: {course.title}")
```

## Adding a New University

The modular architecture makes adding new universities straightforward:

### 1. Create a new scraper module

```python
# coursecrusader/scrapers/universities/myschool.py

from ..base import BaseCourseScraper
from ..registry import register_scraper

@register_scraper
class MySchoolScraper(BaseCourseScraper):
    name = "myschool"
    university = "My School University"
    start_urls = ['https://catalog.myschool.edu/courses/']

    def parse(self, response):
        # Find course pages
        for course_link in response.css('a.course::attr(href)').getall():
            yield response.follow(course_link, self.parse_course)

    def parse_course(self, response):
        # Extract course data
        course = self.create_course(
            course_id=response.css('.course-code::text').get(),
            title=response.css('.course-title::text').get(),
            description=response.css('.description::text').get(),
            credits=self.normalize_credits(response.css('.credits::text').get()),
            level=self.infer_level(course_id),
            department=response.css('.department::text').get(),
            **self.parse_prerequisites(response.css('.prereqs::text').get())
        )
        yield course
```

### 2. Register it

Import in `coursecrusader/scrapers/universities/__init__.py`:

```python
from .myschool import MySchoolScraper

__all__ = [..., 'MySchoolScraper']
```

### 3. Test it

```bash
coursecrusader scrape --school myschool --limit 10
coursecrusader validate myschool_courses.jsonl
```

That's it! The base class handles:
- Prerequisite parsing
- Text cleaning
- Credit normalization
- Course validation
- Level inference
- Statistics tracking

## Architecture

### Project Structure

```
Course_crusader/
├── coursecrusader/
│   ├── __init__.py           # Package initialization
│   ├── schema.py             # JSON Schema definition
│   ├── models.py             # Course and metadata models
│   ├── settings.py           # Scrapy settings
│   ├── middlewares.py        # Scrapy middlewares
│   ├── pipelines.py          # Data processing pipelines
│   ├── cli.py                # Command-line interface
│   ├── parsers/              # Parsing utilities
│   │   ├── prerequisites.py  # Prerequisite parser
│   │   ├── text_utils.py     # Text cleaning utilities
│   │   └── pdf_parser.py     # PDF catalog parser
│   └── scrapers/
│       ├── base.py           # Base scraper class
│       ├── registry.py       # Scraper registry
│       └── universities/     # University-specific scrapers
│           ├── uconn.py
│           ├── mit.py
│           └── yale.py
├── tests/                    # Test suite
│   ├── test_models.py
│   ├── test_prerequisites.py
│   ├── test_text_utils.py
│   └── test_schema.py
├── requirements.txt          # Dependencies
├── setup.py                  # Package setup
├── pyproject.toml           # Modern Python config
└── README.md                # This file
```

### Design Principles

1. **Separation of Concerns**: Parsing logic separated from scraping logic
2. **Plugin Architecture**: New scrapers register automatically via decorators
3. **Fail-Safe Parsing**: Uncertain parses flagged, not silently misinterpreted
4. **Extensibility**: Base classes provide common functionality, overridable for special cases
5. **Data Quality**: Validation at multiple stages (parse-time, pipeline, CLI)

## Prerequisites Parser

The prerequisite parser handles complex logical expressions:

```python
from coursecrusader.parsers import PrerequisiteParser

parser = PrerequisiteParser()

# Simple AND
parser.parse("CSE 1010 and CSE 1729")
# → {"and": ["CSE 1010", "CSE 1729"]}

# Simple OR
parser.parse("MATH 1131Q or MATH 1151Q")
# → {"or": ["MATH 1131Q", "MATH 1151Q"]}

# Nested logic
parser.parse("CSE 2100 and (MATH 2210Q or MATH 2410Q)")
# → {"and": ["CSE 2100", {"or": ["MATH 2210Q", "MATH 2410Q"]}]}
```

Features:
- Extracts course codes in various formats
- Handles AND/OR logic with parentheses
- Recognizes non-course requirements (e.g., "junior standing")
- Flags uncertain parses for review

## PDF Support

For universities with PDF catalogs:

```python
from coursecrusader.parsers import PDFCourseScraper

scraper = PDFCourseScraper(
    university="Sample University",
    department="Computer Science"
)

for course in scraper.scrape_pdf("https://example.edu/catalog.pdf"):
    print(f"{course['course_id']}: {course['title']}")
```

The PDF parser:
- Downloads PDFs directly from URLs (no manual download needed)
- Handles broken lines and formatting issues
- **NEW**: Multi-column layout detection and proper text extraction
- Extracts structured course data
- Uses pdfplumber (better) or PyPDF2 (fallback)

## Advanced Features (Phase 3-5)

### SQLite Database Support

Export and query course data using SQLite:

```bash
# Import JSONL to database
coursecrusader import-db uconn_courses.jsonl

# View database statistics
coursecrusader db-stats

# Search courses
coursecrusader search "calculus" --university UConn --limit 5
```

Python API:

```python
from coursecrusader.database import CourseDatabase

db = CourseDatabase("courses.db")

# Get all courses for a university
courses = db.get_courses_by_university("UConn")

# Search by keyword
results = db.search_courses("data structures", university="MIT")

# Get statistics
stats = db.get_statistics()
print(f"Total courses: {stats['total_courses']}")
print(f"Prerequisite parse rate: {stats['prerequisite_parse_rate']}%")

db.close()
```

### Change Detection & Automated Refresh

Monitor catalogs for updates and automatically re-scrape when changes are detected:

```python
from coursecrusader.refresh import ChangeDetector, RefreshScheduler

# Detect changes
detector = ChangeDetector("snapshots.json")
has_changed, reason = detector.check_for_changes(
    university="UConn",
    url="https://catalog.uconn.edu/courses/"
)

if has_changed:
    print(f"Catalog changed: {reason}")
    # Trigger re-scraping

# Automated refresh scheduling
scheduler = RefreshScheduler(detector)
should_refresh, reason = scheduler.should_refresh("UConn", catalog_url)

# Get refresh priorities
priorities = scheduler.get_refresh_priority()
for university, priority in priorities[:5]:
    print(f"{university}: priority {priority}")
```

Features:
- Content hash-based change detection
- Configurable check intervals
- Priority-based refresh scheduling
- Stale catalog identification
- Automatic snapshot management

### Data Quality Validation

Measure scraper accuracy against manually verified golden datasets:

```python
from coursecrusader.validation import GoldenDatasetValidator

# Create golden dataset sample for verification
from coursecrusader.validation import create_golden_sample
create_golden_sample(
    "uconn_courses.jsonl",
    "golden_sample.json",
    sample_size=50
)

# After manual verification, validate scraped data
validator = GoldenDatasetValidator("golden_verified.json")
report = validator.validate_dataset("uconn_courses.jsonl")

# Print detailed report
validator.print_report(report)
```

Validation metrics:
- Field-by-field accuracy (course_id, title, credits, etc.)
- Completeness rates
- Error identification
- Overall quality scores

### Performance Monitoring

Profile scraper performance and resource usage:

```python
from coursecrusader.performance import PerformanceMonitor, profile_scraper

# Monitor a scraping run
monitor = PerformanceMonitor()
metrics = monitor.start_monitoring("UConn")

# ... run scraper ...

monitor.update_metrics("UConn", courses=1000, pages=50)
monitor.end_monitoring("UConn")
monitor.print_summary()

# Context manager for automatic profiling
with profile_scraper("MIT") as metrics:
    # Run scraper
    metrics.update(courses=2000, pages=100)
# Automatically prints performance summary
```

Performance metrics tracked:
- Duration and courses/second rate
- Page fetch count
- Memory peak usage
- Error count

## Testing

Run the test suite:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=coursecrusader --cov-report=term-missing

# Run specific test file
pytest tests/test_prerequisites.py

# Run with verbose output
pytest -v
```

## Development

### Code Quality

```bash
# Format code
black coursecrusader/

# Lint
flake8 coursecrusader/

# Type checking
mypy coursecrusader/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-university`)
3. Add your university scraper
4. Write tests for it
5. Ensure all tests pass (`pytest`)
6. Submit a pull request

## Data Quality Goals

### Phase 1 (MVP)
- ✅ Unified schema for all schools
- ✅ 3-5 universities supported
- ✅ 90%+ course capture rate
- ✅ Required fields populated for 95%+ of courses
- ✅ Basic prerequisite parsing

### Phase 2 (Production)
- 🎯 10+ universities
- 🎯 97%+ course capture rate
- 🎯 95-99% accuracy on course codes, titles, credits
- 🎯 Advanced prerequisite parsing (80%+ structured)
- 🎯 API rate limiting and caching
- 🎯 Automated testing and CI/CD

## Use Cases

- **Course Search Engines**: Build cross-university course discovery tools
- **Transfer Credit Analysis**: Map equivalent courses between institutions
- **Academic Planning**: Analyze course prerequisites and plan degree paths
- **Research**: Study curriculum patterns across universities
- **Data Analysis**: Explore trends in course offerings, credits, etc.

## Performance

- **UConn**: ~1000 courses in ~5 minutes (with rate limiting)
- **MIT**: ~2000 courses in ~10 minutes
- **Memory**: < 100MB typical usage
- **Caching**: HTTP cache reduces repeated scrapes

## Troubleshooting

### Common Issues

**Import errors:**
```bash
pip install -r requirements.txt
pip install -e .
```

**Validation failures:**
```bash
# Check data quality
coursecrusader validate your_courses.jsonl

# Test with limited scrape
coursecrusader scrape --school uconn --limit 10
```

**Slow scraping:**
- Adjust `DOWNLOAD_DELAY` in `coursecrusader/settings.py`
- Use `--limit` for testing

## License

MIT License - see LICENSE file for details

## Citation

If you use Course Crusader in research, please cite:

```
@software{coursecrusader2025,
  title={Course Crusader: Unified Course Catalog Scraper},
  author={Course Crusader Team},
  year={2025},
  url={https://github.com/BenjaminSRussell/Course_crusader}
}
```

## Acknowledgments

Inspired by:
- [CourseCake](https://github.com/nananananate/CourseCake) - Multi-school scraper framework
- Various university catalog systems (CourseLeaf, Acalog, custom)

## Support

- **Issues**: https://github.com/BenjaminSRussell/Course_crusader/issues
- **Discussions**: https://github.com/BenjaminSRussell/Course_crusader/discussions

---

**Built with:** Python 3.8+, Scrapy, BeautifulSoup, pdfplumber, Click

**Status:** Alpha - API may change
