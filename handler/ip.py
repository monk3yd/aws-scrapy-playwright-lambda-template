import scrapy

from scrapy import signals
from scrapy.utils.log import configure_logging
# from scrapy.exceptions import CloseSpider

from loguru import logger
from playwright.async_api import expect, Page, TimeoutError as PlaywrightTimeoutError


configure_logging()
class IPPlaywrightSpider(scrapy.Spider):
    name = "ip_playwright_spider"

    def __init__(self, kwargs):
        self.state = "init"
        logger.debug(f"Spider {self.name}: OK")

        logger.debug(f"Spider input: {kwargs}")

    def start_requests(self):
        self.state = "start"
        yield scrapy.Request(
            url="http://checkip.amazonaws.com/",
            method="GET",
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                # playwright_context="persistent"
            ),
            callback=self.parse,
            errback=self.close_page,
            dont_filter=True
        )

    async def parse(self, response):
        self.state = "parse"
        page: Page = response.meta["playwright_page"]
        ip = await page.locator("pre").text_content()

        # Middleware
        # await page.context.route("**/*", self.__handle_route)

        logger.debug(f"My IP: {ip}")
        yield {"ip": ip}


    async def __handle_route(self, route):
        request = route.request
        logger.info(f"Route URL ({request.method}): {request.url}")

        if request.method == "GET":
            self.__request_headers = request.headers
            logger.info(f"Request headers: {self.__request_headers}")

            self.__request_url = request.url
            logger.info(f"Request URL: {self.__request_url}")

        await route.continue_()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(IPPlaywrightSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        spider.stats = crawler.stats.get_stats()
        return spider

    def spider_closed(self, spider):
        self.state = "OK"
        spider.stats["state"] = self.state


    async def close_page(self, failure):
        page = failure.request.meta["playwright_page"]

        # request = failure.request
        # response = failure.value.response

        self.reboot = True
        await page.close()
