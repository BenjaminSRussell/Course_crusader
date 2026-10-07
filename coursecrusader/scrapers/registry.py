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


def readiness_matrix():
    """Return sorted list of (name, university, readiness) for all scrapers (#7)."""
    rows = []
    for name, cls in sorted(ScraperRegistry.get_all().items()):
        rows.append(
            (
                name,
                getattr(cls, "university", "?"),
                getattr(cls, "readiness", "STUB"),
            )
        )
    return rows


def write_status_md(path=None):
    """Regenerate docs/SCRAPER_STATUS.md from the registry (no hand drift)."""
    from pathlib import Path as _P

    path = _P(path) if path else _P(__file__).resolve().parents[2] / "docs" / "SCRAPER_STATUS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = readiness_matrix()
    nl = chr(10)
    lines_out = [
        "# Scraper readiness matrix",
        "",
        "Auto-generated from `ScraperRegistry` — run `coursecrusader status --write`",
        "to refresh. Do not hand-edit the table by hand.",
        "",
        "| key | university | status |",
        "|-----|------------|--------|",
    ]
    for name, uni, status in rows:
        lines_out.append(f"| `{name}` | {uni} | **{status}** |")
    stub = sum(1 for *_, s in rows if s == "STUB")
    ready = sum(1 for *_, s in rows if s == "READY")
    lines_out += [
        "",
        f"Totals: **{ready} READY**, **{stub} STUB**, {len(rows)} registered.",
        "",
    ]
    path.write_text(nl.join(lines_out))
    return path


if __name__ == "__main__":
    print(write_status_md())
