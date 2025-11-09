"""
University-specific scrapers.

Each module in this package implements a scraper for a specific university.
All scrapers are automatically registered via the @register_scraper decorator.
"""

# Import all university scrapers to auto-register them
try:
    from .uconn import UConnScraper
except ImportError:
    UConnScraper = None

try:
    from .mit import MITScraper
except ImportError:
    MITScraper = None

try:
    from .yale import YaleScraper
except ImportError:
    YaleScraper = None

__all__ = [
    'UConnScraper',
    'MITScraper',
    'YaleScraper',
]
