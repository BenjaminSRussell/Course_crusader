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
from .scrapers.universities import *
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
    scraper_class = ScraperRegistry.get(school.lower())

    if not scraper_class:
        click.echo(f"❌ Error: No scraper found for '{school}'", err=True)
        click.echo(f"\nAvailable scrapers:", err=True)
        for name in ScraperRegistry.list_scrapers():
            click.echo(f"  - {name}", err=True)
        sys.exit(1)

    if not output:
        output = f"{school.lower()}_courses.{format}"

    click.echo(f"🚀 Starting scrape for {scraper_class.university}")
    click.echo(f"📁 Output: {output} ({format})")

    settings = get_project_settings()

    feed_format = 'jsonlines' if format == 'jsonl' else format
    settings.set('FEEDS', {
        output: {
            'format': feed_format,
            'encoding': 'utf-8',
            'overwrite': True,
        }
    })

    if limit:
        settings.set('CLOSESPIDER_ITEMCOUNT', limit)
        click.echo(f"⚠️  Limited to {limit} courses (testing mode)")

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

        click.echo(f"📊 Validation Results:")
        click.echo(f"  Total courses: {total}")
        click.echo(f"  Valid courses: {valid}")
        click.echo(f"  Invalid courses: {len(errors)}")
        click.echo(f"  Success rate: {(valid/total*100):.1f}%\n")

        if errors:
            click.echo("⚠️  Validation Errors:\n")
            for error in errors[:10]:
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


@main.command()
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--database',
    '-d',
    type=click.Path(),
    default='courses.db',
    help='SQLite database file (default: courses.db)'
)
def import_db(file: str, database: str):
    """
    Import course data from JSONL/JSON file into SQLite database.

    Example:

        coursecrusader import-db uconn_courses.jsonl

        coursecrusader import-db data.jsonl --database my_courses.db
    """
    from .database import CourseDatabase
    from .models import Course

    click.echo(f"📥 Importing {file} into {database}...")

    try:
        db = CourseDatabase(database)
        file_path = Path(file)
        count = 0

        if file_path.suffix == '.jsonl':
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        course_data = json.loads(line)
                        course = Course(**course_data)
                        db.insert_course(course)
                        count += 1
        elif file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                courses_data = data if isinstance(data, list) else [data]
                for course_data in courses_data:
                    course = Course(**course_data)
                    db.insert_course(course)
                    count += 1

        db.close()
        click.echo(f"✅ Imported {count} courses into {database}")

    except Exception as e:
        click.echo(f"❌ Error importing: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    '--database',
    '-d',
    type=click.Path(exists=True),
    default='courses.db',
    help='SQLite database file'
)
@click.option(
    '--university',
    '-u',
    help='Filter by university'
)
def db_stats(database: str, university: Optional[str]):
    """
    Display statistics about the course database.

    Example:

        coursecrusader db-stats

        coursecrusader db-stats --university UConn
    """
    from .database import CourseDatabase

    try:
        db = CourseDatabase(database)

        if university:
            courses = db.get_courses_by_university(university)
            click.echo(f"\n📊 Statistics for {university}:")
            click.echo(f"  Total courses: {len(courses)}")
        else:
            stats = db.get_statistics()
            click.echo("\n📊 Database Statistics:\n")
            click.echo(f"  Total courses: {stats['total_courses']}")
            click.echo(f"\n  By University:")
            for uni, count in stats['by_university'].items():
                click.echo(f"    {uni}: {count}")
            click.echo(f"\n  By Level:")
            for level, count in stats['by_level'].items():
                click.echo(f"    {level}: {count}")
            click.echo(f"\n  Prerequisite Parse Rate: {stats['prerequisite_parse_rate']}%")

        db.close()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('query')
@click.option(
    '--database',
    '-d',
    type=click.Path(exists=True),
    default='courses.db',
    help='SQLite database file'
)
@click.option(
    '--university',
    '-u',
    help='Filter by university'
)
@click.option(
    '--limit',
    '-l',
    type=int,
    default=10,
    help='Maximum results to show'
)
def search(query: str, database: str, university: Optional[str], limit: int):
    """
    Search courses in the database by title or description.

    Example:

        coursecrusader search "data structures"

        coursecrusader search "calculus" --university MIT
    """
    from .database import CourseDatabase

    try:
        db = CourseDatabase(database)
        result = db.search_courses(query, university, limit=limit)
        results = result["rows"]

        if not results:
            click.echo(f"No courses found matching '{query}'")
            return

        click.echo(f"\n🔍 Found {result['total']} matching courses (showing {len(results)}):\n")

        for i, course in enumerate(results):
            click.echo(f"{i+1}. {course['university']} {course['course_id']}: {course['title']}")
            if course.get('description'):
                desc = course['description'][:100] + "..." if len(course['description']) > 100 else course['description']
                click.echo(f"   {desc}\n")

        if result.get("truncated"):
            click.echo(f"... and {result['total'] - len(results)} more results")

        db.close()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()


@cli.command('corequisite')
@click.argument('course_id')
@click.option(
    '--database',
    '-d',
    type=click.Path(exists=True),
    default='courses.db',
    help='SQLite database file',
)
@click.option('--university', '-u', help='Filter by university')
def corequisite(course_id: str, database: str, university: Optional[str]):
    """List courses that list COURSE_ID as a corequisite."""
    from .database import CourseDatabase

    db = CourseDatabase(database)
    try:
        result = db.courses_with_corequisite(course_id, university)
        rows = result["rows"]
        if not rows:
            click.echo(f"No courses list '{course_id}' as a corequisite")
            return
        click.echo(f"Found {len(rows)} course(s) with corequisite {course_id}:")
        for course in rows:
            click.echo(f"  {course['university']} {course['course_id']}: {course['title']}")
        if result.get("skipped_invalid"):
            click.echo(f"(skipped {result['skipped_invalid']} row(s) with invalid JSON)")
    finally:
        db.close()


@cli.command('offered')
@click.argument('term')
@click.option(
    '--database',
    '-d',
    type=click.Path(exists=True),
    default='courses.db',
    help='SQLite database file',
)
def offered(term: str, database: str):
    """List courses offered in TERM (Fall/Spring/Summer/Winter/Year-round)."""
    from .database import CourseDatabase

    db = CourseDatabase(database)
    try:
        result = db.courses_offered_in(term)
        rows = result["rows"]
        if not rows:
            click.echo(f"No courses offered in '{term}'")
            return
        click.echo(f"Found {len(rows)} course(s) offered in {term}:")
        for course in rows:
            click.echo(f"  {course['university']} {course['course_id']}: {course['title']}")
        if result.get("skipped_invalid"):
            click.echo(f"(skipped {result['skipped_invalid']} row(s) with invalid JSON)")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(2)
    finally:
        db.close()
