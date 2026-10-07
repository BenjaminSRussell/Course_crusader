"""Scraper contract: create_course required fields + infer_level (#14)."""

import pytest

from coursecrusader.models import Course
from coursecrusader.scrapers.base import BaseCourseScraper


class _ContractSpider(BaseCourseScraper):
    name = "contract_test"
    university = "ContractU"
    readiness = "STUB"

    def parse(self, response):  # pragma: no cover
        return
        yield


@pytest.fixture
def spider():
    return _ContractSpider()


REQUIRED = ("university", "course_id", "title", "description", "credits", "level", "department")


def test_create_course_fills_university_and_validates(spider):
    course = spider.create_course(
        course_id="CSE 2100",
        title="Data Structures",
        description="Trees, graphs, hashing.",
        credits=3,
        level="Undergraduate",
        department="CSE",
    )
    assert course.university == "ContractU"
    assert course.last_updated
    ok, errors = course.validate()
    assert ok, errors
    for field in REQUIRED:
        assert getattr(course, field)


def test_create_course_missing_department_fails_validate(spider):
    course = spider.create_course(
        course_id="CSE 1010",
        title="Intro",
        description="Basics",
        credits=3,
        level="Undergraduate",
        department="",
    )
    ok, errors = course.validate()
    assert not ok
    assert any("department" in e for e in errors)


@pytest.mark.parametrize(
    "course_id,expected",
    [
        ("CSE 1000", "Undergraduate"),
        ("CSE 1999", "Undergraduate"),
        ("CSE 2000", "Undergraduate"),
        ("CSE 2999", "Undergraduate"),
        ("MATH 101", "Undergraduate"),
        ("CSE 5100", "Graduate"),
        ("CSE 9999", "Graduate"),
        ("GRAD", "Unknown"),
        ("", "Unknown"),
    ],
)
def test_infer_level_edges(spider, course_id, expected):
    assert Course.infer_level(course_id) == expected
    assert spider.infer_level(course_id) == expected


def test_validate_course_delegates(spider):
    course = spider.create_course(
        course_id="BIO 1100",
        title="Bio",
        description="Cells",
        credits=4,
        level="Undergraduate",
        department="Biology",
    )
    assert spider.validate_course(course) == course.validate()
