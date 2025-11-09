"""
Command-line interface for Course Crusader.

Provides easy-to-use commands for scraping university course catalogs.
"""

import click
import sys
import json
from pathlib import Path
from typing import Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from .scrapers.registry import ScraperRegistry
from .scrapers.universities import *  # Import all scrapers to register them
from .__init__ import __version__


@click.group()
@click.version_option(version=__version__)
def main():
    """
    Course Crusader - Unified Course Catalog Scraper

    Scrape and normalize university course catalogs into a unified JSON format.
    """
    pass


@main.command()
@click.option(
    '--school',
    '-s',
    required=True,
    help='University identifier (e.g., uconn, mit)'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Output file path (default: {school}_courses.jsonl)'
)
@click.option(
    '--format',
    '-f',
    type=click.Choice(['jsonl', 'json', 'csv'], case_sensitive=False),
    default='jsonl',
    help='Output format (default: jsonl)'
)
@click.option(
    '--limit',
    '-l',
    type=int,
    help='Limit number of courses to scrape (for testing)'
)
def scrape(school: str, output: Optional[str], format: str, limit: Optional[int]):
    """
    Scrape course catalog for a specific university.

    Examples:

        coursecrusader scrape --school uconn

        coursecrusader scrape --school uconn --output courses.jsonl

        coursecrusader scrape -s uconn -f json -o data.json
    """
    # Get scraper class
    scraper_class = ScraperRegistry.get(school.lower())

    if not scraper_class:
        click.echo(f"❌ Error: No scraper found for '{school}'", err=True)
        click.echo(f"\nAvailable scrapers:", err=True)
        for name in ScraperRegistry.list_scrapers():
            click.echo(f"  - {name}", err=True)
        sys.exit(1)

    # Determine output file
    if not output:
        output = f"{school.lower()}_courses.{format}"

    click.echo(f"🚀 Starting scrape for {scraper_class.university}")
    click.echo(f"📁 Output: {output} ({format})")

    # Configure Scrapy settings
    settings = get_project_settings()

    # Set output format
    feed_format = 'jsonlines' if format == 'jsonl' else format
    settings.set('FEEDS', {
        output: {
            'format': feed_format,
            'encoding': 'utf-8',
            'overwrite': True,
        }
    })

    # Set limit if specified
    if limit:
        settings.set('CLOSESPIDER_ITEMCOUNT', limit)
        click.echo(f"⚠️  Limited to {limit} courses (testing mode)")

    # Run scraper
    try:
        process = CrawlerProcess(settings)
        process.crawl(scraper_class)
        process.start()

        click.echo(f"\n✅ Scraping complete! Output saved to: {output}")

    except Exception as e:
        click.echo(f"\n❌ Error during scraping: {e}", err=True)
        sys.exit(1)


@main.command()
def list():
    """
    List all available university scrapers.
    """
    scrapers = ScraperRegistry.get_all()

    if not scrapers:
        click.echo("No scrapers registered.")
        return

    click.echo("📚 Available University Scrapers:\n")

    for name, scraper_class in sorted(scrapers.items()):
        university = scraper_class.university
        click.echo(f"  {name:15} - {university}")

    click.echo(f"\nTotal: {len(scrapers)} scrapers")
    click.echo("\nUsage: coursecrusader scrape --school <name>")


@main.command()
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--limit',
    '-l',
    type=int,
    help='Number of courses to display (default: all)'
)
def validate(file: str, limit: Optional[int]):
    """
    Validate a scraped course catalog file.

    Checks if courses conform to the schema and reports any issues.
    """
    click.echo(f"🔍 Validating: {file}\n")

    try:
        # Read file
        courses = []
        file_path = Path(file)

        if file_path.suffix == '.jsonl':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        courses.append(json.loads(line))
        elif file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                courses = data if isinstance(data, list) else [data]
        else:
            click.echo(f"❌ Unsupported file format: {file_path.suffix}", err=True)
            sys.exit(1)

        # Validate courses
        from .models import Course

        total = len(courses)
        valid = 0
        errors = []

        display_count = limit if limit else total

        for i, course_data in enumerate(courses[:display_count]):
            try:
                course = Course(**course_data)
                is_valid, course_errors = course.validate()

                if is_valid:
                    valid += 1
                else:
                    errors.append({
                        'course': f"{course.university} {course.course_id}",
                        'errors': course_errors
                    })

            except Exception as e:
                errors.append({
                    'course': f"Course #{i+1}",
                    'errors': [str(e)]
                })

        # Report results
        click.echo(f"📊 Validation Results:")
        click.echo(f"  Total courses: {total}")
        click.echo(f"  Valid courses: {valid}")
        click.echo(f"  Invalid courses: {len(errors)}")
        click.echo(f"  Success rate: {(valid/total*100):.1f}%\n")

        if errors:
            click.echo("⚠️  Validation Errors:\n")
            for error in errors[:10]:  # Show first 10 errors
                click.echo(f"  {error['course']}:")
                for err in error['errors']:
                    click.echo(f"    - {err}")
                click.echo()

            if len(errors) > 10:
                click.echo(f"  ... and {len(errors) - 10} more errors")

    except Exception as e:
        click.echo(f"❌ Error reading file: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    required=True,
    help='Output file for merged data'
)
def merge(files: tuple, output: str):
    """
    Merge multiple course catalog files into one.

    Useful for combining data from different universities.

    Example:

        coursecrusader merge uconn.jsonl mit.jsonl -o combined.jsonl
    """
    click.echo(f"🔗 Merging {len(files)} files...\n")

    all_courses = []

    for file_path in files:
        click.echo(f"  Reading: {file_path}")
        path = Path(file_path)

        try:
            if path.suffix == '.jsonl':
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            all_courses.append(json.loads(line))
            elif path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_courses.extend(data)
                    else:
                        all_courses.append(data)

        except Exception as e:
            click.echo(f"❌ Error reading {file_path}: {e}", err=True)
            sys.exit(1)

    # Write merged output
    output_path = Path(output)

    try:
        if output_path.suffix == '.jsonl':
            with open(output_path, 'w', encoding='utf-8') as f:
                for course in all_courses:
                    f.write(json.dumps(course) + '\n')
        elif output_path.suffix == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_courses, f, indent=2, ensure_ascii=False)
        else:
            click.echo(f"❌ Unsupported output format: {output_path.suffix}", err=True)
            sys.exit(1)

        click.echo(f"\n✅ Merged {len(all_courses)} courses to: {output}")

    except Exception as e:
        click.echo(f"❌ Error writing output: {e}", err=True)
        sys.exit(1)


@main.command()
def schema():
    """
    Display the JSON schema for course data.
    """
    from .schema import COURSE_SCHEMA

    click.echo("📋 Course Catalog JSON Schema:\n")
    click.echo(json.dumps(COURSE_SCHEMA, indent=2))


if __name__ == '__main__':
    main()
