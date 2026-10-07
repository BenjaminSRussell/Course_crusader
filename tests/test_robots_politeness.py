"""Robots politeness settings (#12)."""

from unittest.mock import MagicMock

from scrapy.exceptions import IgnoreRequest

from coursecrusader import settings as project_settings
from coursecrusader.middlewares import PolitenessLoggingMiddleware


def test_robots_obey_enabled():
    assert project_settings.ROBOTSTXT_OBEY is True
    mws = project_settings.DOWNLOADER_MIDDLEWARES
    assert any("RobotsTxtMiddleware" in k for k in mws)
    assert any("PolitenessLoggingMiddleware" in k for k in mws)


def test_download_delay_default():
    assert float(project_settings.DOWNLOAD_DELAY) >= 1.0


def test_politeness_middleware_logs_robots_skip():
    crawler = MagicMock()
    mw = PolitenessLoggingMiddleware.from_crawler(crawler)
    spider = MagicMock()
    spider.custom_settings = {"DOWNLOAD_DELAY": 1.5}
    spider.settings = MagicMock()
    spider.settings.get.return_value = 1.0
    request = MagicMock()
    request.url = "https://catalog.example.edu/disallowed"
    # Should not raise; returns None so Scrapy keeps IgnoreRequest
    out = mw.process_exception(request, IgnoreRequest("Forbidden by robots.txt"), spider)
    assert out is None
    assert spider.logger.info.called
