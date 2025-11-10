#!/usr/bin/env python3
"""
Automated course catalog refresh script.

Runs scrapers for all configured universities, checking for changes
and updating the database. Designed to run as a cron job.

Usage:
    python scripts/automated_refresh.py
    python scripts/automated_refresh.py --university UConn
    python scripts/automated_refresh.py --force
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from coursecrusader.refresh import ChangeDetector, RefreshScheduler
from coursecrusader.scrapers.registry import ScraperRegistry
from coursecrusader.scrapers.universities import *  # Import all scrapers
from coursecrusader.database import CourseDatabase
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


UNIVERSITY_CONFIGS = {
    'uconn': {
        'name': 'UConn',
        'url': 'https://catalog.uconn.edu/course-descriptions/',
        'enabled': True
    },
    'mit': {
        'name': 'MIT',
        'url': 'http://catalog.mit.edu/subjects/',
        'enabled': True
    },
    'yale': {
        'name': 'Yale',
        'url': 'https://catalog.yale.edu/courses/',
        'enabled': True
    }
}

SNAPSHOT_FILE = "catalog_snapshots.json"
DATABASE_FILE = "courses.db"
LOG_FILE = "automated_refresh.log"


def setup_logging(verbose=False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


def run_scraper(university_key: str, output_file: str, limit: int = None):
    """
    Run scraper for a specific university.

    Args:
        university_key: University identifier (e.g., 'uconn')
        output_file: Output JSONL file path
        limit: Optional limit on number of courses

    Returns:
        Number of courses scraped
    """
    scraper_class = ScraperRegistry.get(university_key)

    if not scraper_class:
        raise ValueError(f"No scraper found for {university_key}")

    settings = get_project_settings()
    settings.set('FEEDS', {
        output_file: {
            'format': 'jsonlines',
            'encoding': 'utf-8',
            'overwrite': True
        }
    })

    if limit:
        settings.set('CLOSESPIDER_ITEMCOUNT', limit)

    process = CrawlerProcess(settings)
    process.crawl(scraper_class)
    process.start()


    course_count = 0
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            course_count = sum(1 for line in f if line.strip())

    return course_count


def import_to_database(jsonl_file: str, db_path: str, logger):
    """
    Import JSONL file to database.

    Args:
        jsonl_file: Path to JSONL file
        db_path: Path to database file
        logger: Logger instance

    Returns:
        Number of courses imported
    """
    import json
    from coursecrusader.models import Course

    db = CourseDatabase(db_path)
    count = 0

    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        course_data = json.loads(line)
                        course = Course(**course_data)
                        db.insert_course(course)
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to import course: {e}")

        logger.info(f"Imported {count} courses to database")

    finally:
        db.close()

    return count


def refresh_university(
    university_key: str,
    config: dict,
    detector: ChangeDetector,
    force: bool,
    logger,
    test_mode: bool = False
):
    """
    Refresh catalog for a single university.

    Args:
        university_key: University identifier
        config: University configuration
        detector: ChangeDetector instance
        force: Force refresh even if no changes
        logger: Logger instance
        test_mode: If True, limit to 10 courses

    Returns:
        Tuple of (success, course_count, message)
    """
    logger.info(f"Checking {config['name']}...")


    has_changed, reason = detector.check_for_changes(
        university=config['name'],
        url=config['url'],
        force=force
    )

    if not has_changed and not force:
        logger.info(f"Skipping {config['name']}: {reason}")
        return False, 0, reason

    logger.info(f"Refreshing {config['name']}: {reason}")

    output_file = f"{university_key}_courses.jsonl"

    try:
        course_count = run_scraper(
            university_key,
            output_file,
            limit=10 if test_mode else None
        )

        logger.info(f"Scraped {course_count} courses from {config['name']}")

    import json
        import_count = import_to_database(output_file, DATABASE_FILE, logger)

        detector.update_snapshot(
            university=config['name'],
            course_count=course_count,
            notes=f"Automated refresh at {datetime.now().isoformat()}"
        )

        db = CourseDatabase(DATABASE_FILE)
        db.record_scrape(
            university=config['name'],
            courses_added=import_count,
            scraper_version="0.1.0",
            notes="Automated refresh"
        )
        db.close()

        logger.info(f"✅ Successfully refreshed {config['name']}")

        return True, course_count, "Success"

    except Exception as e:
        logger.error(f"❌ Error refreshing {config['name']}: {e}")
        return False, 0, str(e)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Automated course catalog refresh")
    parser.add_argument(
        '--university', '-u',
        help='Specific university to refresh (e.g., uconn)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force refresh even if no changes detected'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test mode (limit to 10 courses per university)'
    )
    parser.add_argument(
        '--max-universities', '-m',
        type=int,
        default=5,
        help='Maximum number of universities to refresh (default: 5)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )

    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    logger.info("=" * 60)
    logger.info("Starting automated course catalog refresh")
    logger.info("=" * 60)


    detector = ChangeDetector(SNAPSHOT_FILE)
    scheduler = RefreshScheduler(detector)


    if args.university:
        if args.university not in UNIVERSITY_CONFIGS:
            logger.error(f"Unknown university: {args.university}")
            sys.exit(1)

        universities_to_refresh = [(args.university, UNIVERSITY_CONFIGS[args.university])]

    else:
        priorities = scheduler.get_refresh_priority()

        universities_to_refresh = [
            (key, config)
            for key, config in UNIVERSITY_CONFIGS.items()
            if config.get('enabled', True)
        ]

        priority_map = {uni: pri for uni, pri in priorities}
        universities_to_refresh.sort(
            key=lambda x: priority_map.get(x[1]['name'], 0),
            reverse=True
        )

        universities_to_refresh = universities_to_refresh[:args.max_universities]

    logger.info(f"Will attempt to refresh {len(universities_to_refresh)} universities")

    results = []
    for uni_key, config in universities_to_refresh:
        success, count, message = refresh_university(
            uni_key,
            config,
            detector,
            args.force,
            logger,
            args.test
        )

        results.append({
            'university': config['name'],
            'success': success,
            'course_count': count,
            'message': message
        })

    logger.info("=" * 60)
    logger.info("Refresh Summary")
    logger.info("=" * 60)

    successful = sum(1 for r in results if r['success'])
    total_courses = sum(r['course_count'] for r in results)

    logger.info(f"Universities refreshed: {successful}/{len(results)}")
    logger.info(f"Total courses: {total_courses}")

    for result in results:
        status = "✅" if result['success'] else "❌"
        logger.info(
            f"{status} {result['university']}: "
            f"{result['course_count']} courses - {result['message']}"
        )

    logger.info("=" * 60)

    sys.exit(0 if successful > 0 else 1)


if __name__ == '__main__':
    main()
