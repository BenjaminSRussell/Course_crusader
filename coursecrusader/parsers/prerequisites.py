"""
Parser for prerequisite requirements.

Converts natural language prerequisite strings into structured logical expressions.
"""

from ..parsers import clean_text

class PrerequisiteParser:
    """
    Parse prerequisite strings into structured format.

    Examples:
        "A and B" -> {"and": ["A", "B"]}
        "A or B" -> {"or": ["A", "B"]}
        "A and (B or C)" ->
            {"and": ["A", {"or": ["B", "C"]}]}
    """

    # Common course code pattern
    COURSE_PATTERN = r'\b([A-Z]{2,6})\s*(\d{3,4}[A-Z]?)\b'

    # Keywords that indicate non-course prerequisites
    NON_COURSE_KEYWORDS = [
        'permission of instructor',
        'instructor consent',
        'department consent',
        'instructor permission',
        'junior standing',
        'senior standing',
        'sophomore standing',
        'freshman standing',
        'graduate standing',
        'admission to',
        'minimum grade',
        'grade of',
        'gpa',
        'open only to',
        'restricted to',
        'majors only',
        'concurrent enrollment',
        'consent required',
        'departmental approval',
        'by invitation',
        'audition required',
       'portfolio review',
        'prerequisite waiver',
    ]

    # Grade requirement patterns
    GRADE_PATTERNS = [
        r'minimum grade of\s+([A-F][+-]?)',
        r'grade of\s+([A-F][+-]?)\s+or\s+(better|higher)',
        r'([A-F][+-]?)\s+or\s+(better|higher)',
    ]

    def __init__(self):
        """Initialize the parser."""
        self.course_regex = re.compile(self.COURSE_PATTERN, re.IGNORECASE)

    def parse(self, prereq_text: str) -> tuple[Optional[Dict[str, Any]], bool]:
        """
        Parse prerequisite text into structured format.

        Args:
            prereq_text: Raw prerequisite string from catalog

        Returns:
            (structured_prereqs, successfully_parsed)
            - structured_prereqs: Nested dict with 'and'/'or' keys, or None
            - successfully_parsed: Boolean indicating confidence in parse
        """
        if not prereq_text or not prereq_text.strip():
            return None, True

        text = clean_text(prereq_text)

        # Check for non-course prerequisites
        non_course_reqs = self._extract_non_course_requirements(text)

        try:
            courses = self._extract_courses(text)

            if not courses:
                # No course codes found - might be all text-based requirements
                if non_course_reqs:
                    return None, False  # Can't structure, but we have info
                return None, True  # Nothing to parse

            structure = self._determine_structure(text, courses)

            # If we have non-course requirements, note them
            if non_course_reqs and structure:
                # For now, we just return the structured courses
                # In future, could add a 'requirements' field
                pass

            return structure, structure is not None

        except Exception:
            return None, False

    def _extract_courses(self, text: str) -> List[str]:
        """
        Extract all course codes from text.

        Returns list of normalized course codes like ["CSE 2100", "MATH 1131Q"]
        """
        courses = []
        for match in self.course_regex.finditer(text):
            dept = match.group(1).upper()
            number = match.group(2).upper()
            courses.append(f"{dept} {number}")

        return courses

    def _extract_non_course_requirements(self, text: str) -> List[str]:
        """Extract non-course requirements like 'junior standing'."""
        requirements = []
        text_lower = text.lower()

        for keyword in self.NON_COURSE_KEYWORDS:
            if keyword in text_lower:
                requirements.append(keyword)

        return requirements

    def _determine_structure(self, text: str, courses: List[str]) -> Optional[Dict[str, Any]]:
        """
        Determine the logical structure of prerequisites.

        Handles:
        - Simple AND: "A and B" -> {"and": ["A", "B"]}
        - Simple OR: "A or B" -> {"or": ["A", "B"]}
        - Nested: "A and (B or C)" -> {"and": ["A", {"or": ["B", "C"]}]}
        """
        text_lower = text.lower()

        # Check for parentheses (nested structure)
        if '(' in text:
            return self._parse_nested(text, courses)

        has_and = ' and ' in text_lower
        has_or = ' or ' in text_lower

        if has_and and has_or:
            # Complex case - try to parse carefully
            return self._parse_complex(text, courses)
        elif has_and:
            return {"and": courses}
        elif has_or:
            return {"or": courses}
        elif len(courses) == 1:
            # Single course - just return it as-is (no wrapper needed)
            return {"and": courses}  # Wrap in 'and' for consistency
        else:
            # Multiple courses with no clear connector - assume AND
            return {"and": courses}

    def _parse_nested(self, text: str, courses: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parse prerequisites with nested parentheses.

        Example: "CSE 2100 and (MATH 2210Q or MATH 2410Q)"
        """
        paren_pattern = r'\(([^)]+)\)'
        matches = list(re.finditer(paren_pattern, text))

        if not matches:
            return self._parse_complex(text, courses)

        # For now, handle single level of nesting
        # More complex nesting would require recursive parsing
        if len(matches) == 1:
            paren_group = matches[0].group(1)
            before_paren = text[:matches[0].start()].strip()
            after_paren = text[matches[0].end():].strip()

            paren_courses = self._extract_courses(paren_group)

            if ' or ' in paren_group.lower():
                paren_struct = {"or": paren_courses}
            else:
                paren_struct = {"and": paren_courses}

            outside_courses = self._extract_courses(before_paren + " " + after_paren)

            if ' and ' in text.lower() and '(' in text:
                all_parts = outside_courses + [paren_struct]
                return {"and": all_parts}
            elif ' or ' in text.lower():
                all_parts = outside_courses + [paren_struct]
                return {"or": all_parts}
            else:
                return paren_struct

        # Multiple levels - too complex, return None
        return None

    def _parse_complex(self, text: str, courses: List[str]) -> Optional[Dict[str, Any]]:
        """
        Handle complex prerequisites with mixed AND/OR.

        This is a simplified version - full implementation would need
        precedence rules (typically AND binds tighter than OR).
        """
        # For now, if both 'and' and 'or' present without parens,
        # we can't reliably parse - return None
        text_lower = text.lower()

        if ' and ' in text_lower and ' or ' in text_lower:
            return None

        return {"and": courses}

    def extract_corequisites(self, text: str) -> Optional[List[str]]:
        """
        Extract corequisite courses from text.

        Looks for patterns like "Corequisite: CSE 1010"
        """
        if not text:
            return None

        coreq_pattern = r'corequisite[s]?\s*:?\s*(.+?)(?:[.;]|$)'
        match = re.search(coreq_pattern, text, re.IGNORECASE)

        if match:
            coreq_text = match.group(1)
            courses = self._extract_courses(coreq_text)
            return courses if courses else None

        return None
