"""Scraper READY/STUB matrix (#7)."""

from coursecrusader.scrapers.universities import *  # noqa: F401,F403
from coursecrusader.scrapers.registry import readiness_matrix, write_status_md


def test_every_scraper_has_explicit_status():
    rows = readiness_matrix()
    assert len(rows) >= 10
    for name, uni, status in rows:
        assert status in {"READY", "STUB"}, name


def test_stub_and_ready_present():
    rows = readiness_matrix()
    statuses = {s for *_, s in rows}
    assert "STUB" in statuses
    assert "READY" in statuses
    by_name = {n: s for n, _, s in rows}
    assert by_name.get("asu") == "STUB"
    assert by_name.get("uconn") == "READY"


def test_status_md_roundtrip(tmp_path):
    path = write_status_md(tmp_path / "SCRAPER_STATUS.md")
    body = path.read_text()
    assert "| key |" in body
    assert "READY" in body and "STUB" in body
