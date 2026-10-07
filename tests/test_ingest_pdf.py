"""PDF ingest fixture path (#10)."""
from pathlib import Path
import pytest

from coursecrusader.parsers.pdf_parser import PDFCatalogParser
from coursecrusader.models import Course


FIXTURE = Path(__file__).parent / "fixtures" / "pdfs" / "sample_catalog.pdf"


def test_fixture_pdf_yields_courses():
    parser = PDFCatalogParser()
    text = parser.parse_pdf_file(str(FIXTURE))
    assert text.strip()
    chunks = parser.split_into_courses(text)
    assert len(chunks) >= 1
    found = 0
    for ch in chunks:
        data = parser.extract_course_from_text(ch)
        if not data:
            continue
        course = Course(
            university="UConn",
            course_id=data["course_id"],
            title=data["title"],
            description=data.get("description") or data["title"],
            credits=data.get("credits") or 3,
            level=Course.infer_level(data["course_id"]),
            department="CSE",
        )
        ok, _ = course.validate()
        if ok:
            found += 1
    assert found >= 1


def test_invalid_pdf_raises():
    parser = PDFCatalogParser()
    with pytest.raises(Exception):
        parser.parse_pdf_bytes(b"not a pdf at all!!!")
