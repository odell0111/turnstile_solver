import datetime
import logging
import time
from pathlib import Path
from typing import Callable, Awaitable
from patchright.async_api import async_playwright, Page, BrowserContext, Browser, Playwright

from . import constants as c
from .enums import CaptchaApiMessageEvent
from .proxy import Proxy
from .solver_console import SolverConsole
from .turnstile_result import TurnstileResult
from .turnstile_solver_server import TurnstileSolverServer, CAPTCHA_EVENT_CALLBACK_ENDPOINT

logger = logging.getLogger(__name__)

BROWSER_ARGS = {
  "--disable-blink-features=AutomationControlled",  # avoid navigator.webdriver detection
  "--no-sandbox",
  "--disable-dev-shm-usage",
  "--disable-background-networking",
  "--disable-background-timer-throttling",
  "--disable-backgrounding-occluded-windows",
  "--disable-renderer-backgrounding",
  '--disable-application-cache',
  '--disable-field-trial-config',
  '--export-tagged-pdf',
  '--force-color-profile=srgb',
  '--safebrowsing-disable-download-protection',
  '--disable-search-engine-choice-screen',
  '--disable-browser-side-navigation',
  '--disable-save-password-bubble',
  '--disable-single-click-autofill',
  '--allow-file-access-from-files',
  '--disable-prompt-on-repost',
  '--dns-prefetch-disable',
  '--disable-translate',
  '--disable-client-side-phishing-detection',
  '--disable-oopr-debug-crash-dump',
  '--disable-top-sites',
  '--ash-no-nudges',
  '--no-crash-upload',
  '--deny-permission-prompts',
  '--simulate-outdated-no-au="Tue, 31 Dec 2099 23:59:59 GMT"',
  '--disable-ipc-flooding-protection',
  '--disable-password-generation',
  '--disable-domain-reliability',
  '--disable-breakpad',
  # Allow Manifest V2 extensions
  # --disable-features=ExtensionManifestV2DeprecationWarning,ExtensionManifestV2Disabled,ExtensionManifestV2Unsupported
  '--disable-features=OptimizationHints,OptimizationHintsFetching,Translate,OptimizationTargetPrediction,OptimizationGuideModelDownloading,DownloadBubble,DownloadBubbleV2,InsecureDownloadWarnings,InterestFeedContentSuggestions,PrivacySandboxSettings4,SidePanelPinning,UserAgentClientHint',
  '--no-pings',
  # '--homepage=chrome://version/',
  '--animation-duration-scale=0',
  '--wm-window-animations-disabled',
  '--enable-privacy-sandbox-ads-apis',
  # '--disable-popup-blocking',
  '--lang=en-US',
  '--no-default-browser-check',
  '--no-first-run',
  '--no-service-autorun',
  '--password-store=basic',
  '--log-level=3',
  '--proxy-bypass-list=<-loopback>;localhost;127.0.0.1;*.local',

  # Not needed, here just for reference
  # Network/Connection Tuning
  # '--enable-features=NetworkService,ParallelDownloading',
  # '--max-connections=255',  # Total active connections
  # '--max-parallel-downloads=50',  # Concurrent downloads
  # '--socket-reuse-policy=2',  # Aggressive socket reuse

  # Thread/Process Management
  # '--renderer-process-limit=0',  # Unlimited renderers
  # '--in-process-gpu',  # Reduce process count # NO
  # '--disable-site-isolation-trials',  # Prevent tab grouping # NO

  # Protocol-Specific
  # '--http2-no-coalesce-host',  # Bypass HTTP/2 coalescing
  # '--force-http2-hpack-huffman=off',  # Reduce HPACK overhead
}


class TurnstileSolver:

  def __init__(self,
               server: TurnstileSolverServer | None,
               page_load_timeout: float = c.PAGE_LOAD_TIMEOUT,
               browser_position: tuple[int, int] | None = c.BROWSER_POSITION,
               browser_executable_path: str | Path | None = None,
               reload_page_on_captcha_overrun_event: bool = False,
               max_attempts: int = c.MAX_ATTEMPTS_TO_SOLVE_CAPTCHA,
               attempt_timeout: int = c.CAPTCHA_ATTEMPT_TIMEOUT,
               headless: bool = False,
               console: SolverConsole = SolverConsole(),
               log_level: int | str = logging.INFO,
               proxy: Proxy | None = None,
               browser_args: list[str] | None = None,
               ):

    logger.setLevel(log_level)
    self.console = console
    self.page_load_timeout = page_load_timeout
    self.reload_page_on_captcha_overrun_event = reload_page_on_captcha_overrun_event
    self.browser_executable_path = browser_executable_path
    self.headless = headless

    self.server: TurnstileSolverServer | None = server

    self.browser_args = list(BROWSER_ARGS) + (browser_args or [])
    if browser_position:
      self.browser_args.append(f'--window-position={browser_position[0]},{browser_position[1]}')
    self._error: str | None = None
    self.max_attempts = max_attempts
    self.attempt_timeout = attempt_timeout

    self.proxy = proxy

  @property
  def _server_down(self) -> bool:
    if self.server.down:
      self._error = "Server down"
      logger.warning("Captcha can't be solved because server is down")
      return True
    return False

  @property
  def error(self) -> str:
    return self._error or 'Unknown'

  async def solve(self,
                  site_url: str,
                  site_key: str,
                  attempts: int | None = None,
                  timeout: float | None = None,
                  page: Page | bool = False,
                  about_blank_on_finish: bool = False,
                  ) -> TurnstileResult | None:
    """
    If page is a Page instance, this instance will be reused, else a new BrowserContext instance will be created and destroyed upon finish if browser_context is False, else the created instance will be returned along with the Browser instance
    """

    if not self.server:
      raise RuntimeError("self.server instance has not been assigned")

    if self.server.down:
      raise RuntimeError("Server is down. Make sure to run server and wait fot it to be up. Use method .wait_for_server_up()")

    if not attempts:
      attempts = self.max_attempts
    if not timeout:
      timeout = self.attempt_timeout
    self._error = None
    site_url = site_url.rstrip('/') + "/"

    startTime = time.time()

    result = TurnstileResult()
    self.server.subscribe_captcha_message_event_handler(result.id, result.captcha_api_message_event_handler)

    onFinishCallbacks: list[Callable[[], Awaitable[None]]] = []

    if isinstance(page, bool):
      pageOrContext, playwright = await self.get_browser_context()
      if page is True:
        result.browser_context = pageOrContext
      else:
        async def _closeBrowserAndConnection():
          result.page = None
          await pageOrContext.close()
          await pageOrContext.browser.close()
          await playwright.stop()
          logging.debug("Browser closed")

        onFinishCallbacks.append(_closeBrowserAndConnection)
    else:  # elif isinstance(page, Page):
      pageOrContext = page

    try:
      for a in range(1, attempts + 1):
        logger.info(f"Attempt: {a}/{attempts}")

        result.reset_captcha_fields()

        # 1. Route and load page, reset captcha fields
        if not (page := await self._setup_page(
            page_or_context=result.page or pageOrContext,
            site_url=site_url,
            site_key=site_key,
            id=result.id,
        )):
          return

        result.page = page

        # 2. Wait for init event
        logger.debug(f"Waiting for '{CaptchaApiMessageEvent.INIT.value}' event")
        try:
          if await result.wait_for_captcha_event(evt=CaptchaApiMessageEvent.INIT, timeout=timeout) is False:
            return
        except TimeoutError as te:
          self._error = te.args[0]
          logger.warning(f"Captcha API message '{CaptchaApiMessageEvent.INIT.value}' event not received within {timeout} seconds")
          continue

        if self._server_down:
          return

        # 3. Wait for 'complete' event
        try:
          cancellingEvents = [CaptchaApiMessageEvent.REJECT, CaptchaApiMessageEvent.FAIL, CaptchaApiMessageEvent.RELOAD_REQUEST]
          if self.reload_page_on_captcha_overrun_event:
            cancellingEvents.append(CaptchaApiMessageEvent.OVERRUN_BEGIN)
          if (cancellingEvent := await result.wait_for_captcha_event(
              *cancellingEvents,
              evt=CaptchaApiMessageEvent.COMPLETE,
              timeout=timeout,
          )) is False:
            return
          elif isinstance(cancellingEvent, CaptchaApiMessageEvent):
            logger.warning(f"'{cancellingEvent.value}' event received")
            continue
        except TimeoutError as te:
          self._error = te.args[0]
          logger.warning(f"Captcha not solved within {timeout} seconds")
          continue

        if result.token is None:
          raise RuntimeError("'result.token' is not supposed to be None at this point")

        elapsed = datetime.timedelta(seconds=time.time() - startTime)
        logger.info(f"Captcha solved. Elapsed: {str(elapsed).split('.')[0]}")
        logger.debug(f"TOKEN: {result.token}")
        result.elapsed = elapsed
        break

      if about_blank_on_finish:
        await page.goto("about:blank")
      if result.token:
        return result
      self._error = f"Captcha failed to solve in {attempts} attempts :("
      logger.error(self._error)
    except Exception as ex:
      self._error = str(ex)
      raise
      # logger.error(ex)
    finally:
      self.server.unsubscribe_captcha_message_event_handler(result.id)
      for callback in onFinishCallbacks:
        await callback()

  async def _setup_page(
      self,
      page_or_context: BrowserContext | Page,
      site_url: str,
      site_key: str,
      id: str,
  ) -> Page | None:

    if self._server_down:
      return

    page = await page_or_context.new_page() if isinstance(page_or_context, BrowserContext) else page_or_context

    pageContent = c.HTML_TEMPLATE.format(
      local_server_port=self.server.port,
      local_callback_endpoint=CAPTCHA_EVENT_CALLBACK_ENDPOINT.lstrip('/'),
      site_key=site_key,
      id=id,
      secret=self.server.secret,
    )
    await page.route(site_url, lambda r: r.fulfill(body=pageContent, status=200))

    if page.url != site_url:
      logger.debug(f"Navigating to URL: {site_url}")
      await page.goto(site_url, timeout=self.page_load_timeout * 1000)
    else:
      logger.debug("Reloading page")
      await page.reload(timeout=self.page_load_timeout * 1000)

    page.window_width = await page.evaluate("window.innerWidth")
    page.window_height = await page.evaluate("window.innerHeight")

    return page

  async def get_browser(self,
                        playwright: Playwright | None = None,
                        proxy: Proxy | None = None,
                        ) -> tuple[Browser, Playwright]:

    proxy = proxy or self.proxy

    if not playwright:
      playwright = await async_playwright().start()

    browser: Browser | None = await playwright.chromium.launch(
      executable_path=self.browser_executable_path,
      # channel=channel,
      args=self.browser_args,
      headless=self.headless,
      proxy=proxy.dict() if proxy else None,
    )
    return browser, playwright

  async def get_browser_context(self,
                                browser: Browser | None = None,
                                playwright: Playwright | None = None,
                                proxy: Proxy | None = None,
                                ) -> tuple[BrowserContext, Playwright]:

    if not browser:
      browser, _ = await self.get_browser(playwright)

    context = await browser.new_context(proxy=proxy.dict() if proxy else None)

    # await context.route('**', lambda route: route.continue_())
    # await context.set_extra_http_headers({'HTTP2-Settings': 'MAX_CONCURRENT_STREAMS=100'})

    return context, playwright
