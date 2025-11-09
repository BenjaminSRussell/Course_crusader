# Contributing to Course Crusader

Thank you for your interest in contributing to Course Crusader! This document provides guidelines for contributing to the project.

## How to Contribute

### Adding a New University Scraper

Adding support for a new university is one of the most valuable contributions. Here's how:

1. **Research the catalog structure**
   - Visit the university's course catalog website
   - Note the URL patterns
   - Identify how courses are organized (by department, alphabetically, etc.)
   - Check the HTML structure of course pages
   - Document any special fields or formats

2. **Create a new scraper file**
   - Copy an existing scraper as a template (e.g., `uconn.py`)
   - Create `coursecrusader/scrapers/universities/yourschool.py`
   - Implement the scraper following the pattern below:

```python
from ..base import BaseCourseScraper
from ..registry import register_scraper

@register_scraper
class YourSchoolScraper(BaseCourseScraper):
    name = "yourschool"  # lowercase, used in CLI
    university = "Your School University"  # full name
    start_urls = ['https://catalog.yourschool.edu/courses/']

    def parse(self, response):
        """Parse the main catalog page."""
        # Your implementation here
        pass
```

3. **Register the scraper**
   - Add import to `coursecrusader/scrapers/universities/__init__.py`

4. **Test thoroughly**
   ```bash
   # Test with limited scrape
   coursecrusader scrape --school yourschool --limit 10

   # Validate output
   coursecrusader validate yourschool_courses.jsonl

   # Run full scrape
   coursecrusader scrape --school yourschool
   ```

5. **Write tests**
   - Add tests in `tests/test_yourschool.py`
   - Test course parsing with sample HTML
   - Verify schema compliance

6. **Document**
   - Add university to README's supported list
   - Note any special handling or quirks
   - Document the catalog structure

### Bug Fixes

1. **Identify the bug**
   - Check if an issue already exists
   - If not, create one with details

2. **Fix the bug**
   - Create a branch: `git checkout -b fix/bug-description`
   - Make your changes
   - Add/update tests to cover the bug

3. **Test**
   ```bash
   pytest tests/
   ```

4. **Submit PR**
   - Clear description of the bug and fix
   - Reference the issue number

### Improving Parsers

The prerequisite parser and text utilities can always be improved:

- Handle more prerequisite formats
- Improve PDF text extraction
- Better credit hour parsing
- Enhanced department name extraction

### Code Quality

Before submitting:

1. **Format code**
   ```bash
   black coursecrusader/
   ```

2. **Check linting**
   ```bash
   flake8 coursecrusader/
   ```

3. **Run tests**
   ```bash
   pytest --cov=coursecrusader
   ```

4. **Update documentation** if needed

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/Course_crusader.git
cd Course_crusader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Pull Request Guidelines

### Title
Use descriptive titles:
- `Add: Support for Stanford University catalog`
- `Fix: Prerequisite parsing for nested OR conditions`
- `Improve: PDF text extraction for multi-column layouts`

### Description
Include:
- What changes were made
- Why they were made
- Any relevant issue numbers
- Testing performed

### Checklist
- [ ] Code follows project style (black formatted)
- [ ] Tests pass (`pytest`)
- [ ] New functionality has tests
- [ ] Documentation updated if needed
- [ ] Commit messages are clear

## Code Style

- **Python**: PEP 8 (enforced by black)
- **Line length**: 100 characters
- **Docstrings**: Google style
- **Type hints**: Encouraged but not required

### Example

```python
def parse_course(self, response) -> Optional[Course]:
    """
    Parse a single course from the response.

    Args:
        response: Scrapy response object containing course page

    Returns:
        Course object or None if parsing fails
    """
    # Implementation
    pass
```

## Testing Guidelines

### Unit Tests
- Test individual functions in isolation
- Use fixtures for sample data
- Mock external dependencies

### Integration Tests
- Test full scraping flow
- Use saved HTML pages (not live sites)
- Verify schema compliance

### Example Test

```python
def test_parse_course_id():
    """Test course ID parsing and normalization."""
    parser = UConnScraper()

    # Test with space
    assert parser.extract_course_id("CSE 2100") == "CSE 2100"

    # Test without space
    assert parser.extract_course_id("CSE2100") == "CSE 2100"

    # Test with hyphen
    assert parser.extract_course_id("CSE-2100") == "CSE 2100"
```

## Commit Messages

Use clear, concise commit messages:

```
Add MIT scraper with custom course ID handling

- Implements scraper for MIT catalog
- Handles MIT's numeric course format (6.001, etc.)
- Adds tests for MIT-specific parsing
- Updates README with MIT in supported list
```

## Questions?

- **General questions**: Open a discussion
- **Bug reports**: Open an issue
- **Feature requests**: Open an issue with "enhancement" label
- **Security issues**: Email maintainers (see README)

## Recognition

Contributors will be recognized in:
- README acknowledgments
- Release notes
- Project website (if created)

Thank you for contributing to Course Crusader!
