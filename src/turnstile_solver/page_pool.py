import logging
from collections import deque

import asyncio

from patchright.async_api import BrowserContext, Page

from .constants import MAX_PAGES_ON_POOL

logger = logging.getLogger(__name__)


class PagePool:
  def __init__(self, context: BrowserContext):
    self.context = context
    self._used_pages = 0
    self._available: deque = deque()
    self._in_use: list[Page] = []
    self._lock = asyncio.Lock()

  @property
  def _is_full(self) -> bool:
    return len(self._in_use) == MAX_PAGES_ON_POOL

  async def get(self) -> Page:
    async with self._lock:
      # Check possible runtime error
      if len(self._in_use) > MAX_PAGES_ON_POOL:
        raise RuntimeError("len(self._in_use) is supposed to be less than self.max_size")
      # Wait for any page to be available
      if self._is_full:
        logger.debug("Waiting for a new page to be available")
        while self._is_full:
          await asyncio.sleep(0.1)
      # Get a page from available ones if any and put it in self._in_use list
      if len(self._available) > 0:
        self._in_use.append(page := self._available.popleft())
        return page
      # Then len(self._in_use) is less than self.max_size, so safely create a new page and put it in self._in_use list
      page = await self.context.new_page()
      self._in_use.append(page)
      logger.debug("New page added to pool")
      return page

  async def put_back(self, page: Page):
    # Check possible runtime error
    if len(self._available) >= MAX_PAGES_ON_POOL:
      raise RuntimeError("len(self._available) is supposed to be less than self.max_size. Make sure to always call put_back() method only if get() method have been called previously")
    # Check possible runtime error again in which provided page may not have been fetched via get() method
    try:
      index = self._in_use.index(page)
    except ValueError:
      raise RuntimeError("The page provided seems not have been fetched via the get() method, and it is supposed to be this way. Make sure to always call put_back() method only if get() method have been called previously")
    logger.debug("Page back on pool")
    self._available.append(self._in_use.pop(index))
