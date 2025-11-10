"""
Scrapy settings for Course Crusader.

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

    https://docs.scrapy.org/en/latest/topics/settings.html
"""

BOT_NAME = 'coursecrusader'

SPIDER_MODULES = ['coursecrusader.scrapers.universities']
NEWSPIDER_MODULE = 'coursecrusader.scrapers.universities'

USER_AGENT = 'CourseCrusader/0.1.0 (+https://github.com/BenjaminSRussell/Course_crusader)'

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 8

DOWNLOAD_DELAY = 1.0
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 8

COOKIES_ENABLED = False

TELNETCONSOLE_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

SPIDER_MIDDLEWARES = {
    'coursecrusader.middlewares.CourseCrusaderSpiderMiddleware': 543,
}

DOWNLOADER_MIDDLEWARES = {
    'coursecrusader.middlewares.CourseCrusaderDownloaderMiddleware': 543,
}

ITEM_PIPELINES = {
    'coursecrusader.pipelines.ValidationPipeline': 100,
    'coursecrusader.pipelines.DeduplicationPipeline': 200,
}

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'

FEEDS = {
    'output.jsonl': {
        'format': 'jsonlines',
        'encoding': 'utf-8',
        'store_empty': False,
        'overwrite': True,
    },
}

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
