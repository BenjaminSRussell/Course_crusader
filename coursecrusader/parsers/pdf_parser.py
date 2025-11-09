"""
PDF parsing utilities for course catalogs.

Handles extraction of text from PDF course catalogs and parsing into
structured course data.
"""

import re
import io
from typing import List, Dict, Optional, Iterator
from urllib.request import urlopen

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


from .text_utils import clean_text, fix_broken_lines, split_course_entries


class PDFCatalogParser:
    """
    Parser for PDF-based course catalogs.

    Extracts text from PDFs and parses into individual course entries.
    """

    def __init__(self, use_pdfplumber: bool = True):
        """
        Initialize PDF parser.

        Args:
            use_pdfplumber: If True and available, use pdfplumber (better layout).
                          Otherwise use PyPDF2.
        """
        self.use_pdfplumber = use_pdfplumber and pdfplumber is not None

        if not self.use_pdfplumber and PyPDF2 is None:
            raise ImportError(
                "Neither pdfplumber nor PyPDF2 is installed. "
                "Install with: pip install pdfplumber PyPDF2"
            )

    def parse_pdf_url(self, url: str) -> str:
        """
        Download and parse PDF from URL.

        Args:
            url: URL to PDF file

        Returns:
            Extracted text content
        """
        # Download PDF
        response = urlopen(url)
        pdf_bytes = response.read()

        # Parse
        return self.parse_pdf_bytes(pdf_bytes)

    def parse_pdf_file(self, file_path: str) -> str:
        """
        Parse PDF from local file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()

        return self.parse_pdf_bytes(pdf_bytes)

    def parse_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Parse PDF from bytes.

        Args:
            pdf_bytes: PDF file as bytes

        Returns:
            Extracted text content
        """
        if self.use_pdfplumber:
            return self._parse_with_pdfplumber(pdf_bytes)
        else:
            return self._parse_with_pypdf2(pdf_bytes)

    def _parse_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Parse PDF using pdfplumber (preserves layout better)."""
        text_parts = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Extract text with layout
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        full_text = '\n\n'.join(text_parts)
        return self._clean_pdf_text(full_text)

    def _parse_with_pypdf2(self, pdf_bytes: bytes) -> str:
        """Parse PDF using PyPDF2 (basic extraction)."""
        text_parts = []

        pdf_file = io.BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_file)

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        full_text = '\n\n'.join(text_parts)
        return self._clean_pdf_text(full_text)

    def _clean_pdf_text(self, text: str) -> str:
        """
        Clean text extracted from PDF.

        Handles common PDF issues like broken lines, extra spaces, etc.
        """
        # Fix broken lines
        text = fix_broken_lines(text)

        # Clean general text
        text = clean_text(text)

        return text

    def split_into_courses(
        self,
        text: str,
        course_pattern: Optional[str] = None
    ) -> List[str]:
        """
        Split PDF text into individual course entries.

        Args:
            text: Full catalog text
            course_pattern: Regex pattern that marks start of a course
                          Default: matches patterns like "CSE 2100. Title"

        Returns:
            List of course entry strings
        """
        if course_pattern is None:
            # Default pattern: Department code followed by number and period
            # Example: "CSE 2100. Data Structures"
            course_pattern = r'\n([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+'

        # Find all course starts
        matches = list(re.finditer(course_pattern, text))

        if not matches:
            # No courses found with pattern
            return []

        courses = []

        for i, match in enumerate(matches):
            start = match.start()

            # End is either the next course or end of text
            if i < len(matches) - 1:
                end = matches[i + 1].start()
            else:
                end = len(text)

            course_text = text[start:end].strip()
            courses.append(course_text)

        return courses

    def extract_course_from_text(
        self,
        course_text: str
    ) -> Optional[Dict[str, str]]:
        """
        Extract course fields from a single course text block.

        Args:
            course_text: Text for one course entry

        Returns:
            Dict with course fields (course_id, title, description, etc.)
            or None if parsing fails
        """
        # Pattern: "DEPT NUM. Title. Credits. Description..."
        # Example: "CSE 2100. Data Structures. 3 credits. Introduction to..."

        # First line usually has course code and title
        lines = course_text.strip().split('\n')
        if not lines:
            return None

        first_line = lines[0]

        # Extract course code and title
        pattern = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+?)(?:\.\s+(\d+(?:\.\d+)?)\s+credits?)?\.?\s*$'
        match = re.match(pattern, first_line)

        if not match:
            # Try simpler pattern
            pattern2 = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+)'
            match = re.match(pattern2, first_line)

        if not match:
            return None

        dept = match.group(1)
        number = match.group(2)
        title = match.group(3).strip().rstrip('.')

        course_id = f"{dept} {number}"

        # Credits might be in match group 4 or in subsequent text
        credits = None
        if len(match.groups()) >= 4:
            credits = match.group(4)

        # Description is the remaining text
        description_parts = lines[1:] if len(lines) > 1 else []

        # If credits not found, look in description
        full_desc = ' '.join(description_parts)

        from .text_utils import extract_credits
        if credits is None:
            credits = extract_credits(full_desc)

        # Look for prerequisites
        prereq_text = None
        prereq_match = re.search(
            r'(?:prerequisite|prereq)[s]?\s*:\s*([^.]+)',
            full_desc,
            re.IGNORECASE
        )
        if prereq_match:
            prereq_text = prereq_match.group(1).strip()

        return {
            'course_id': course_id,
            'title': title,
            'description': full_desc.strip(),
            'credits': credits,
            'prerequisites_text': prereq_text,
        }


class PDFCourseScraper:
    """
    Helper class for scraping courses from PDF catalogs.

    Can be used standalone or integrated with Scrapy spiders.
    """

    def __init__(self, university: str, department: str = "Unknown"):
        """
        Initialize PDF course scraper.

        Args:
            university: University name
            department: Default department for courses
        """
        self.university = university
        self.department = department
        self.parser = PDFCatalogParser()

    def scrape_pdf(
        self,
        pdf_url: str,
        course_pattern: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Scrape courses from a PDF URL.

        Args:
            pdf_url: URL to PDF catalog
            course_pattern: Optional regex pattern for course identification

        Yields:
            Course dictionaries
        """
        # Parse PDF
        text = self.parser.parse_pdf_url(pdf_url)

        # Split into courses
        course_texts = self.parser.split_into_courses(text, course_pattern)

        # Parse each course
        for course_text in course_texts:
            course_data = self.parser.extract_course_from_text(course_text)

            if course_data:
                # Add university and department
                course_data['university'] = self.university
                course_data['department'] = self.department
                course_data['catalog_url'] = pdf_url

                # Infer level
                from ..models import Course
                if 'level' not in course_data:
                    course_data['level'] = Course.infer_level(course_data['course_id'])

                yield course_data
