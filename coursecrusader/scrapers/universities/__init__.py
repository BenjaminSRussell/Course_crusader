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

try:
    from .stanford import StanfordScraper
except ImportError:
    StanfordScraper = None

try:
    from .berkeley import BerkeleyScraper
except ImportError:
    BerkeleyScraper = None

try:
    from .harvard import HarvardScraper
except ImportError:
    HarvardScraper = None

try:
    from .cornell import CornellScraper
except ImportError:
    CornellScraper = None

try:
    from .princeton import PrincetonScraper
except ImportError:
    PrincetonScraper = None

__all__ = [
    'UConnScraper',
    'MITScraper',
    'YaleScraper',
    'StanfordScraper',
    'BerkeleyScraper',
    'HarvardScraper',
    'CornellScraper',
    'PrincetonScraper',
]
