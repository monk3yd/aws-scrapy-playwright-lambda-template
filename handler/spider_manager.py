import multiprocessing

from loguru import logger

from scrapy.settings import Settings
from scrapy.crawler import CrawlerRunner

# Manually install asyncio reactor for scrapy-playwright compatibility
from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

from twisted.internet import reactor


class SpiderManager:
    def __init__(self):
        logger.debug("SpiderManager: OK")

        # Configuration
        HEADLESS = True
        CHROMIUM_ARGS = [
            "--no-sandbox",
            "--disable-setuid-sandbox",  # Disable the setuid sandbox (Linux only)
            "--disable-blink-features=AutomationControlled",
            "--ignore-default-args=--enable-automation",
            "--single-process",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-zygote",
            "--enable-logging",
            "--ignore-certificate-errors",
            "--log-level=0",
            "--v=0",
            "--window-size='1440x1696'",
            # f"--data-path={TMP_FOLDER}/data-path",
            # f"--homedir={TMP_FOLDER}",
            # f"--disk-cache-dir={TMP_FOLDER}/cache-dir",
            # f"--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"",
        ]
        if HEADLESS:
            CHROMIUM_ARGS.append("--headless=new")

        self.settings = Settings()
        self.settings.set("ROBOTSTXT_OBEY", False)
        self.settings.set("LOG_LEVEL", "DEBUG")
        self.settings.set("REQUEST_FINGERPRINTER_IMPLEMENTATION", "2.7")

        self.settings.set("PLAYWRIGHT_BROWSER_TYPE", "chromium")
        self.settings.set("PLAYWRIGHT_CONTEXTS", {
            "default": {
                "viewport": {"width": 1440, "height": 1000},
            },
            # "persistent": {
            #     "user_data_dir": "playwright-persistent/"
            # }
        })
        # Ignored when using persistent context
        self.settings.set("PLAYWRIGHT_LAUNCH_OPTIONS", {
            "headless": HEADLESS,
            "slow_mo": 1000,
            "args": CHROMIUM_ARGS,
        })
        # Use playwright headers instead of scrapys
        self.settings.set("PLAYWRIGHT_PROCESS_REQUEST_HEADERS", None)
        self.settings.set("PLAYWRIGHT_ABORT_REQUEST", lambda req: req.resource_type == "image")
        self.settings.set("DOWNLOAD_HANDLERS", {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        })
        # self.settings.set("TWISTED_REACTOR", "twisted.internet.asyncioreactor.AsyncioSelectorReactor")
        self.settings.set("FEED_EXPORT_ENCODING", "utf-8")
        logger.debug("Settings: OK")

    def run_spider(self, spider, event):
        processes = []
        p = multiprocessing.Process(target=self._crawl,  args=(spider, event,))
        processes.append(p)
        p.start()
        for process in processes:
            process.join()
        return p

    def _crawl(self, spider, event):
        runner = CrawlerRunner(self.settings)
        deferred = runner.crawl(spider, event)
        deferred.addBoth(lambda _: reactor.stop())
        reactor.run()
