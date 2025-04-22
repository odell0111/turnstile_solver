import logging

from patchright.async_api import BrowserContext, Page, Route
from turnstile_solver.pool import Pool

from turnstile_solver.constants import MAX_PAGES_PER_CONTEXT

logger = logging.getLogger(__name__)


class PagePool(Pool):
  def __init__(self,
               context: BrowserContext,
               max_pages: int = MAX_PAGES_PER_CONTEXT,
               ):
    self.context = context

    super().__init__(
      size=max_pages,
      item_getter=self._page_getter,
    )

  async def _page_getter(self):
    page = await self.context.new_page()
    return page
