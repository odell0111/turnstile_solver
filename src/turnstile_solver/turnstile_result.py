import datetime
import time
from typing import Any

import asyncio

from patchright.async_api import BrowserContext, Page

from .enums import CaptchaApiMessageEvent
from .utils import password


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

  def captcha_api_message_event_handler(self, evt: CaptchaApiMessageEvent, data: dict[str, Any]):
    if evt == CaptchaApiMessageEvent.COMPLETE:
      self.token = data['token']

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
