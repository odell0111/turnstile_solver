# -*- mode: python ; coding: utf-8 -*-
import logging
import time
from inspect import isawaitable
from types import NoneType
from typing import Callable, Any, Awaitable

from typing import TYPE_CHECKING

import asyncio

from quart import Quart, Response, request

from turnstile_solver.enums import CaptchaApiMessageEvent
from turnstile_solver.constants import PORT, HOST, CAPTCHA_EVENT_CALLBACK_ENDPOINT, MAX_CONTEXTS, MAX_PAGES_PER_CONTEXT
from turnstile_solver.proxy_provider import ProxyProvider
from turnstile_solver.solver_console import SolverConsole
from turnstile_solver.constants import SECRET
from turnstile_solver.browser_context_pool import BrowserContextPool

if TYPE_CHECKING:
  from .solver import TurnstileSolver

logger = logging.getLogger(__name__)


class TurnstileSolverServer:

  MessageEventHandler = Callable[[CaptchaApiMessageEvent, dict[str, Any]], NoneType | Awaitable[None]]

  def __init__(self,
               host: str = HOST,
               port: int = PORT,
               disable_access_logs: bool = True,
               ignore_food_events: bool = False,
               turnstile_solver: "TurnstileSolver" = None,
               on_shutting_down: Callable[..., Awaitable[None]] | None = None,
               console: SolverConsole = SolverConsole(),
               log_level: str | int = logging.INFO,
               secret: str = SECRET,
               ):
    logger.setLevel(log_level)
    if disable_access_logs:
      logging.getLogger('hypercorn.access').disabled = True
    self.app = _Quart(__name__)
    self.host = host
    self.port = port
    self.console = console
    self.solver: "TurnstileSolver" = turnstile_solver
    self.down: bool = True
    self._captcha_message_event_handlers: dict[str, TurnstileSolverServer.MessageEventHandler] = {}
    self.on_shutting_down = on_shutting_down
    # /solve endpoint intended fields
    # self.browser_context: BrowserContext | None = None
    self.browser_context_pool: BrowserContextPool | None = None
    # deprecated
    # self.page_pool: PagePool | None = None
    self.secret = secret
    self.ignore_food_events = ignore_food_events

    self._lock = asyncio.Lock()
    self._setup_routes()

  def _setup_routes(self) -> None:
    """Set up the application routes."""
    self.app.before_request(self._before_request)
    self.app.after_request(self._after_request)
    self.app.post(CAPTCHA_EVENT_CALLBACK_ENDPOINT)(self._handle_captcha_message_event)
    self.app.get('/solve')(self._solve)
    self.app.get('/')(self._index)

  def subscribe_captcha_message_event_handler(self, id: str, handler: MessageEventHandler):
    logger.debug(f"Captcha message event handler with id '{id}' subscribed")
    self._captcha_message_event_handlers[id] = handler

  def unsubscribe_captcha_message_event_handler(self, id: str):
    logger.debug(f"Captcha message event handler with id '{id}' unsubscribed")
    self._captcha_message_event_handlers.pop(id, None)

  async def create_browser_context_pool(self,
                                        max_contexts: int = MAX_CONTEXTS,
                                        max_pages_per_context: int = MAX_PAGES_PER_CONTEXT,
                                        single_instance: bool = False,
                                        proxy_provider: ProxyProvider | None = None,
                                        ):
    assert self.solver is not None
    self.browser_context_pool = BrowserContextPool(
      solver=self.solver,
      max_contexts=max_contexts,
      max_pages_per_context=max_pages_per_context,
      single_instance=single_instance,
      proxy_provider=proxy_provider,
    )
    await self.browser_context_pool.init()

  # deprecated
  # async def create_page_pool(self):
  #   """Create PagePool instance to be used in /solve endpoint requests"""
  #   browser_context, _ = await self.solver._get_browser_context()
  #   self.page_pool = PagePool(browser_context)

  async def wait_for_server(self, timeout: float = 5):
    endTime = time.time() + timeout
    while self.down:
      await asyncio.sleep(0.01)
      if time.time() >= endTime:
        raise TimeoutError(f"Server didn't start after {timeout} seconds")

  async def run(self, debug: bool = False):

    async def beforeServing():
      self.down = False
      logger.info("Server up and running")

    async def afterServing():
      self.down = True
      logger.info("Server is down")
      if callable(self.on_shutting_down):
        await self.on_shutting_down()

    self.app.before_serving(beforeServing)
    self.app.after_serving(afterServing)
    await self.app.run_task(
      host=self.host,
      port=self.port,
      debug=debug,
    )

  async def _handle_captcha_message_event(self):
    try:
      logger.debug('Handling captcha message event')
      data: dict[str, Any] = await request.get_json(force=True)
      evt: CaptchaApiMessageEvent | str | None = data.pop('event', None)
      if not evt:
        return self._bad(f"message has no event entry. Data: {data}", log=True)
      try:
        evt = CaptchaApiMessageEvent(evt)
      except ValueError:
        return self._bad(f"Unknown event: '{evt}'")

      if not (id := request.args.get("id")):
        return self._bad("id parameter not specified")

      if not self._captcha_message_event_handlers:
        return self._error("There's no handlers for handling captcha event", warning=True)
      else:
        handler = self._captcha_message_event_handlers.get(id)
        if not handler:
          return self._error(f"There's no handler for handling event with ID: {id}", warning=True)
        if evt != CaptchaApiMessageEvent.FOOD or not self.ignore_food_events:
          logger.debug(f"Dispatching '{evt.value}' event")
        if isawaitable(a := handler(evt, data)):
          await a

    except Exception:
      self.console.print_exception()
      return self._error(self.solver.error, log=False)
    return self._ok()

  async def _solve(self):
    try:
      if self.solver is None:
        return self._error("No TurnstileSolver instance has been assigned")

      if not self.browser_context_pool:
        return self._error("No BrowserContextPool instance has been assigned")

      data: dict[str, str] = await request.get_json(force=True)
      if not (site_url := data.get('site_url')):
        return self._bad("site_url required")
      if not (site_key := data.get('site_key')):
        return self._bad("site_key required")

      async with self._lock:
        pagePool = await self.browser_context_pool.get()
        page = await pagePool.get()

      try:
        if not (result := await self.solver.solve(
            site_url=site_url,
            site_key=site_key,
            page=page,
            about_blank_on_finish=True,
        )):
          return self._error(self.solver.error)
      finally:
        await self.browser_context_pool.put_back(pagePool)
        await pagePool.put_back(page)

      self._page = result.page
      return self._ok({
        "token": result.token,
        "elapsed": str(result.elapsed.total_seconds()),
      })
    except Exception as ex:
      self.console.print_exception()
      return self._error(str(ex))

  async def _before_request(self):
    if request.headers.get('secret') != self.secret:
      logging.error("Forbidden")
      return self._error("Who are you?", 403, "Forbidden")

  async def _after_request(self, res: Response):
    res.headers.update({"Access-Control-Allow-Origin": "*"})
    return res

  async def _index(self):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Turnstile Solver</title>
    </head>
    <body>
      <h2>Turnstile Solver</h2>
    </body>
    </html>"""

  def _bad(self, message: str, log: bool = False, warning: bool = False) -> tuple[dict[str, str], int]:
    return self._error(message, 400, log=log, warning=warning)

  def _error(self, message: str, status_code: int = 500, status="error", log: bool = True, warning: bool = False) -> tuple[dict[str, str], int]:
    if log:
      logger.log(logging.WARNING if warning else logging.ERROR, message)
    return self._json(status, message, status_code)

  def _ok(self, additional_data: dict | None = None) -> tuple[dict[str, str], int]:
    return self._json("OK", None, 200, additional_data)

  def _json(self, status: str, message: str | None, status_code: int, additional_data: dict | None = None) -> tuple[dict[str, str], int]:
    """JSON response template"""
    data = {"status": status, "message": message}
    if additional_data:
      data |= additional_data
    return data, status_code


class _Quart(Quart):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def make_default_options_response(self) -> Response:
    res = await super().make_default_options_response()
    res.headers |= {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "*",
      "Access-Control-Allow-Private-Network": "true",
    }
    return res
