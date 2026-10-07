"""
Parsing utilities for course catalog data.
"""

# Import text_utils BEFORE prerequisites to avoid circular import (#18)
from .text_utils import clean_text, normalize_whitespace, extract_credits
from .prerequisites import PrerequisiteParser
from .pdf_parser import PDFCatalogParser, PDFCourseScraper

__all__ = [
    'PrerequisiteParser',
    'clean_text',
    'normalize_whitespace',
    'extract_credits',
    'PDFCatalogParser',
    'PDFCourseScraper',
]
