"""
Scraper registry for managing multiple university scrapers.

Provides a plugin-like architecture where new scrapers can be easily registered.
"""

from typing import Dict, Type, Optional, List
from .base import BaseCourseScraper


class ScraperRegistry:
    """
    Registry for managing university-specific scrapers.

    Allows dynamic registration and retrieval of scrapers.
    """

    _scrapers: Dict[str, Type[BaseCourseScraper]] = {}

    @classmethod
    def register(cls, scraper_class: Type[BaseCourseScraper]) -> None:
        """
        Register a scraper class.

        Args:
            scraper_class: Scraper class inheriting from BaseCourseScraper
        """
        if not issubclass(scraper_class, BaseCourseScraper):
            raise ValueError(f"{scraper_class} must inherit from BaseCourseScraper")

        # Use the scraper's name attribute as the key
        name = scraper_class.name
        if not name or name == "base_scraper":
            raise ValueError(f"Scraper must have a unique 'name' attribute")

        cls._scrapers[name] = scraper_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseCourseScraper]]:
        """
        Get a scraper class by name.

        Args:
            name: Scraper name (e.g., 'uconn', 'mit')

        Returns:
            Scraper class or None if not found
        """
        return cls._scrapers.get(name.lower())

    @classmethod
    def list_scrapers(cls) -> List[str]:
        """
        List all registered scrapers.

        Returns:
            List of scraper names
        """
        return list(cls._scrapers.keys())

    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseCourseScraper]]:
        """
        Get all registered scrapers.

        Returns:
            Dict mapping scraper names to classes
        """
        return cls._scrapers.copy()


def register_scraper(scraper_class: Type[BaseCourseScraper]) -> Type[BaseCourseScraper]:
    """
    Decorator to automatically register a scraper class.

    Usage:
        @register_scraper
        class UConnScraper(BaseCourseScraper):
            name = "uconn"
            ...
    """
    ScraperRegistry.register(scraper_class)
    return scraper_class
