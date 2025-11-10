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

try:
    from .test import TestScraper
except ImportError:
    TestScraper = None

try:
    from .test1 import Test1Scraper
except ImportError:
    Test1Scraper = None

try:
    from .test2 import Test2Scraper
except ImportError:
    Test2Scraper = None

try:
    from .test3 import Test3Scraper
except ImportError:
    Test3Scraper = None

__all__ = [
    'UConnScraper', 'MITScraper', 'YaleScraper', 'StanfordScraper',
    'BerkeleyScraper', 'HarvardScraper', 'CornellScraper', 'PrincetonScraper',
    'TestScraper', 'Test1Scraper', 'Test2Scraper', 'Test3Scraper',
]
