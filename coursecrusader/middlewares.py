"""
Scrapy middlewares for Course Crusader.
"""

from scrapy import signals


class CourseCrusaderSpiderMiddleware:
    """Spider middleware for Course Crusader."""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info(f"Spider opened: {spider.name}")


class CourseCrusaderDownloaderMiddleware:
    """Downloader middleware for Course Crusader."""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info(f"Spider opened: {spider.name}")


class PolitenessLoggingMiddleware:
    """Log robots.txt denials and remind operators of DOWNLOAD_DELAY (#12)."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def __init__(self, crawler):
        self.crawler = crawler

    def process_exception(self, request, exception, spider):
        # RobotsTxtMiddleware raises IgnoreRequest for Disallow
        name = type(exception).__name__
        if "IgnoreRequest" in name or "RobotsTxt" in name or "robots" in str(exception).lower():
            spider.logger.info(
                "robots.txt skipped %s (school delay=%s)",
                request.url,
                (
                    spider.custom_settings.get("DOWNLOAD_DELAY")
                    if getattr(spider, "custom_settings", None)
                    else spider.settings.get("DOWNLOAD_DELAY")
                ),
            )
        return None
