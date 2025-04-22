import asyncio
import logging
from typing import TYPE_CHECKING

from patchright.async_api import Browser

from turnstile_solver.constants import MAX_PAGES_PER_CONTEXT, MAX_CONTEXTS
from turnstile_solver.page_pool import PagePool
from turnstile_solver.pool import Pool
from turnstile_solver.proxy_provider import ProxyProvider

if TYPE_CHECKING:
  from turnstile_solver.solver import TurnstileSolver

logger = logging.getLogger(__name__)


class BrowserContextPool(Pool):
  def __init__(self,
               solver: "TurnstileSolver",
               max_contexts: int = MAX_CONTEXTS,
               max_pages_per_context: int = MAX_PAGES_PER_CONTEXT,
               single_instance: bool = False,
               proxy_provider: ProxyProvider | None = None,
               ):
    self._solver = solver
    self._browser: Browser | None = None
    self._max_pages_per_context = max_pages_per_context
    self._get_lock = asyncio.Lock()
    self._playwright = None
    self._proxy_provider = proxy_provider
    self._single_instance = single_instance

    super().__init__(
      size=max_contexts,
      item_getter=self._page_pool_getter,
    )

  @property
  def browser(self) -> Browser | None:
    return self._browser

  async def init(self):
    self._browser, _ = await self._solver.get_browser(None)

  async def get(self) -> PagePool:

    if not self._browser:
      raise RuntimeError("'self._browser' instance has not been assigned. Make sure to call init() method at least once")

    # logger.debug('Acquiring lock to fetch PagePool')
    async with self._get_lock:
      # logger.debug('Fetching PagePool')
      for pool in self.in_use:
        if not pool.is_full:
          # logger.debug(f"Reusing PagePool (size = {pool.size})")
          return pool
      # logger.debug("Getting PagePool from pool manager")
      return await super().get()

  async def _page_pool_getter(self):
    proxy = self._proxy_provider.get() if self._proxy_provider else None
    proxy and logger.debug(f"Using proxy: '{proxy.server}'")
    logger.debug(f"Getting browser context for browser: '{self._browser}'")
    context, self._playwright = await self._solver.get_browser_context(
      browser=self._browser if self._single_instance else None,
      playwright=self._playwright,
      proxy=proxy,
    )
    pool = PagePool(context, self._max_pages_per_context)
    return pool
