import datetime
import logging
import time
from typing import Any

import asyncio

from patchright.async_api import BrowserContext, Page

from turnstile_solver.enums import CaptchaApiMessageEvent
from turnstile_solver.utils import password

logger = logging.getLogger(__name__)

_CLICK_CHECKBOX_SCRIPT = """
  let containerWidth = document.querySelector('.cf-turnstile').width;
  let width = containerWidth * 0.2;
  document.querySelector('.cf-turnstile').width = width;
"""


class TurnstileResult:
  def __init__(self,
               token: str | None = None,
               elapsed: datetime.timedelta | None = None,
               browser_context: BrowserContext | None = None,
               page: Page | None = None,
               ):
    self.token = token
    self.elapsed = elapsed
    self.browser_context = browser_context
    self.page = page
    self._id = password(10)
    self._received_captcha_events: set[CaptchaApiMessageEvent] = set()

  @property
  def id(self) -> str:
    return self._id

  async def captcha_api_message_event_handler(self, evt: CaptchaApiMessageEvent, data: dict[str, Any]):
    if evt == CaptchaApiMessageEvent.COMPLETE:
      self.token = data['token']
    elif evt == CaptchaApiMessageEvent.INTERACTIVE_BEGIN:
      # Wait some time?
      # import random
      # await asyncio.sleep(random.uniform(0.1, 0.5))
      await self.click_checkbox()
    self._received_captcha_events.add(evt)

  def reset_captcha_fields(self):
    self._received_captcha_events.clear()
    self.token = None

  async def wait_for_captcha_event(self,
                                   *cancelling_evts: CaptchaApiMessageEvent,
                                   evt: CaptchaApiMessageEvent,
                                   timeout: float,
                                   sleep_time: float = 0.05,
                                   ) -> CaptchaApiMessageEvent | bool:
    endTime = time.time() + timeout
    while True:
      if evt in self._received_captcha_events:
        return True
      elif cancelling_evts:
        for e in cancelling_evts:
          if e in self._received_captcha_events:
            return e
      if time.time() >= endTime:
        raise TimeoutError(f"Captcha event '{evt.value}' not received within {timeout} seconds")
      await asyncio.sleep(sleep_time)

  async def click_checkbox(self, page: Page | None = None):
    page = page or self.page
    # Uncomment these lines if you think CAPTCHA solving process is failing because of the absence of a delay
    # import random
    # await asyncio.sleep(random.uniform(2, 3))
    await page.evaluate(_CLICK_CHECKBOX_SCRIPT)
    # TODO: For some sites this click approach seems to be detected by Cloudflare causing the CAPTCHA solving process to fail (Example site • https://chat.deepseek.com/ 0x4AAAAAAA1jQEh8YFk064tz)
    # await page.click(".cf-turnstile")
    # await page.locator("//div[@class='cf-turnstile']").click(timeout=1000)
    try:
      await page.locator('.cf-turnstile').click(timeout=1000)
      logger.debug("Attempt to click checkbox performed")
    except TimeoutError:
      logger.error("Captcha widget click timed-out")
