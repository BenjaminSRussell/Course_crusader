"""
Text parsing and cleaning utilities.
"""

import re
from typing import Optional, Union


def clean_text(text: str) -> str:
    """
    Clean and normalize text from HTML/PDF sources.

    Handles:
    - Multiple spaces/newlines
    - HTML entities
    - Strange unicode characters
    - Extra punctuation
    """
    if not text:
        return ""

    text = normalize_whitespace(text)

    # Remove common HTML artifacts
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)

    # Fix common PDF issues (broken lines)
    text = fix_broken_lines(text)

    # Remove extra punctuation
    text = re.sub(r'\s+([.,;:])', r'\1', text)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Normalize all whitespace to single spaces."""
    if not text:
        return ""

    # Replace all whitespace (including newlines, tabs) with single space
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def fix_broken_lines(text: str) -> str:
    """
    Fix lines broken in the middle of words (common in PDFs).

    Example:
        "This is a sen-\\ntence." -> "This is a sentence."
    """
    # Join hyphenated words across line breaks
    text = re.sub(r'-\s*\n\s*', '', text)

    # Join lines that don't end with sentence terminators
    text = re.sub(r'(?<![.!?;:])\n(?=[a-z])', ' ', text)

    return text


def extract_credits(text: str) -> Optional[Union[int, float, str]]:
    """
    Extract credit hours from text.

    Handles formats like:
    - "3 credits"
    - "3 cr."
    - "(3)"
    - "3-4 credits"
    - "variable credit"

    Returns:
        Number (int/float) for fixed credits, string for ranges/variable
    """
    if not text:
        return None

    # Pattern for credit hours
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:credits?|cr\.?|hours?)',  # "3 credits", "3 cr"
        r'\((\d+(?:\.\d+)?)\)',  # "(3)"
        r'(\d+)-(\d+)\s*(?:credits?|cr\.?)',  # "3-4 credits"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                # Range like "3-4"
                return f"{match.group(1)}-{match.group(2)}"
            else:
                credit_str = match.group(1)
                # Return as int if whole number, else float
                if '.' in credit_str:
                    return float(credit_str)
                else:
                    return int(credit_str)

    if re.search(r'variable|varies', text, re.IGNORECASE):
        return "variable"

    return None


def split_course_entries(text: str, delimiter_pattern: str = r'\n\s*\n') -> list:
    """
    Split text into individual course entries.

    Args:
        text: Full catalog text
        delimiter_pattern: Regex pattern that separates courses

    Returns:
        List of course entry strings
    """
    entries = re.split(delimiter_pattern, text)
    return [e.strip() for e in entries if e.strip()]


def extract_department(text: str, course_id: str = "") -> Optional[str]:
    """
    Extract department name from text or course ID.

    Args:
        text: Text that might contain department name
        course_id: Course code like "CSE 2100"

    Returns:
        Department name or None
    """
    # Try to extract from course ID prefix
    if course_id:
        match = re.match(r'^([A-Z]{2,6})', course_id)
        if match:
            prefix = match.group(1)
            # This is just the code - we'd need a mapping to get full name
            # For now, return the prefix
            return prefix

    # Try to extract from common patterns in text
    dept_patterns = [
        r'Department of ([^,.\n]+)',
        r'Offered by:?\s*([^,.\n]+)',
    ]

    for pattern in dept_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None
