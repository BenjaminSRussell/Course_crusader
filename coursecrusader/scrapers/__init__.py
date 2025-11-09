"""
Course catalog scrapers for different universities.
"""

from .base import BaseCourseScraper
from .registry import ScraperRegistry, register_scraper

__all__ = ['BaseCourseScraper', 'ScraperRegistry', 'register_scraper']
