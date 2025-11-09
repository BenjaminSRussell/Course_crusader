"""
Course Crusader - Unified Course Catalog Scraper

A modular framework for scraping and normalizing university course catalogs
from multiple institutions into a unified JSON schema.
"""

__version__ = "0.1.0"

from .models import Course, CatalogMetadata
from .scrapers import BaseCourseScraper, ScraperRegistry, register_scraper

__all__ = [
    "Course",
    "CatalogMetadata",
    "BaseCourseScraper",
    "ScraperRegistry",
    "register_scraper",
    "__version__",
]
