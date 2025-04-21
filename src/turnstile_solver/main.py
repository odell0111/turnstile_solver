import asyncio
import logging

import argparse
import random
import time

import dotenv
from pathlib import Path
from threading import Thread

import requests
from pyngrok import ngrok
from pyngrok.ngrok import NgrokTunnel
from rich import traceback
from rich.align import Align
from rich.console import Group
from rich.text import Text
from multiprocessing import Process

from turnstile_solver import constants as c
from turnstile_solver.proxy import Proxy
from turnstile_solver.proxy_provider import ProxyProvider
from turnstile_solver.custom_rich_help_formatter import CustomRichHelpFormatter
from turnstile_solver.solver_console import SolverConsole
from turnstile_solver.solver_console_highlighter import SolverConsoleHighlighter
from turnstile_solver.solver import TurnstileSolver
from turnstile_solver.utils import init_logger, simulate_intensive_task, get_file_handler, load_proxy_param
from turnstile_solver.turnstile_solver_server import TurnstileSolverServer

_console = SolverConsole()

__pname__ = "Turnstile Solver"

# mdata = metadata.metadata(__pname__)
# __version__ = mdata['Version']
__version__ = "3.12"
__homepage__ = "https://github.com/odell0111/turnstile_solver"  # mdata['Home-page']
__author__ = "OGM"  # mdata['Author']
__summary__ = "Automatically solve Cloudflare Turnstile captcha"  # mdata['Summary']

logger = logging.getLogger(__name__)


def _parse_arguments():
  def conditionalTitleCase(s):
    return ' '.join(word if word.isupper() else word.title() for word in s.split())

  CustomRichHelpFormatter.group_name_formatter = conditionalTitleCase

  description = [
    f"{__pname__}",
    f"v{__version__}",
    f'by {__author__}',
    '2024-2025'
  ]

  # noinspection PyTypeChecker
  parser = argparse.ArgumentParser(
    usage="\n  %(prog)s [options]",
    description=Group(*[Align(line, align='center') for line in description]),
    epilog=Align(Text(__homepage__, style=c.CONSOLE_THEME_STYLES['repr.url']), align='center'),
    add_help=False,
    formatter_class=CustomRichHelpFormatter
  )

  def positive_integer(value):
    try:
      value = int(value)
      if value <= 0:
        raise argparse.ArgumentTypeError(f'{value} is not a positive integer')
    except ValueError:
      raise argparse.ArgumentTypeError(f'"{value}" is not an integer')
    return value

  def positive_float(value):
    try:
      value = float(value)
      if value <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive number")
    except ValueError:
      raise argparse.ArgumentTypeError(f'"{value}" is not a number')
    return value

  def positive_float_exclusive(value):
    try:
      value = float(value)
      if value != -1 and value <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive number")
    except ValueError:
      raise argparse.ArgumentTypeError(f'"{value}" is not a number')
    return value

  def positive_integer_exclusive(value):
    try:
      value = int(value)
      if value != -1 and value <= 0:
        raise argparse.ArgumentTypeError(f"{value} is not a positive integer")
    except ValueError:
      raise argparse.ArgumentTypeError(f'"{value}" is not an integer')
    return value

  parser.add_argument("-bep", "--browser-executable-path", help=f"Chromium-based browser executable path. If not specified, Patchright (Playwright) will attempt to use its bundled version. Ensure you are using a Chromium-based browser installed with the command `patchright install chromium`. Other browsers may be detected by Cloudflare, which could result in the CAPTCHA not being solved.")
  parser.add_argument("-bp", "--browser-position", type=int, nargs='*', metavar="x|y", default=c.BROWSER_POSITION, help=f"Browser position x, y. Default: {c.BROWSER_POSITION}. If the browser window is positioned beyond the screen's resolution, it will be inaccessible, behaving similar to headless mode.")
  parser.add_argument("-mbi", "--multiple-browser-instances", action='store_true', help=f"Whether to use a new browser instance for each context or not. This is not recommended since it can occupy a lot more memory. Also the initialization process for each instance can take a little more time so when running for production it's recommended to make some requests to initialize some instances. See '--max-contexts'.")
  parser.add_argument("-mc", "--max-contexts", type=int, metavar="N", default=c.MAX_CONTEXTS, help=f"Max browser contexts. Default: {c.MAX_CONTEXTS}. Memory consumption increases proportionally with the number of browser contexts, specially if a new browser instance is created for each browser context.")
  parser.add_argument("-mp", "--max-pages", type=int, metavar="N", default=c.MAX_PAGES_PER_CONTEXT, help=f"Max pages per browser. Default: {c.MAX_PAGES_PER_CONTEXT}. CAPTCHA-solving speed is impacted by the number of active pages (tabs) within a browser context.")
  parser.add_argument("-ba", "--browser-args", nargs='+', help=f"Additional browser command line arguments.")

  parser.add_argument("-ps", "--proxy-server", help=f"Global browser proxy server in the format: 'scheme://server:port'. Ex: http://myproxy.com:3128")
  parser.add_argument("-pun", "--proxy-username", help=f"Global browser proxy username: Use all caps to load from environment variables.")
  parser.add_argument("-pp", "--proxy-password", help=f"Global browser proxy password: Use all caps to load from environment variables.")
  parser.add_argument("--proxies", metavar='PROXIES.txt', help=f"Path to a .txt file containing proxies in the format: 'scheme://server:port@username:password'. Each browser context will be assigned a unique proxy from this list.")

  parser.add_argument("-nfl", "--no-file-logs", action="store_true", help=f"Do not log to file '$HOME.turnstile_solver/logs.log'.")
  parser.add_argument("-ll", "--log-level", type=int, default=logging.INFO, metavar="N", help=f"Global logger log level. Default: {logging.INFO}. CRITICAL = 50, FATAL = CRITICAL, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0")

  # Solver
  solver = parser.add_argument_group("Solver")
  solver.add_argument("-ma", "--max-attempts", type=positive_integer, metavar="N", default=c.MAX_ATTEMPTS_TO_SOLVE_CAPTCHA, help=f"Max attempts to perform to solve captcha. Default: {c.MAX_ATTEMPTS_TO_SOLVE_CAPTCHA}.")
  solver.add_argument("-cto", "--captcha-timeout", type=positive_float, metavar="N.", default=c.CAPTCHA_ATTEMPT_TIMEOUT, help=f"Max time to wait for captcha to solve before reloading page. Default: {c.CAPTCHA_ATTEMPT_TIMEOUT} seconds.")
  solver.add_argument("-plto", "--page-load-timeout", type=positive_float, metavar="N.", default=c.CAPTCHA_ATTEMPT_TIMEOUT, help=f"Page load timeout. Default: {c.PAGE_LOAD_TIMEOUT} seconds.")
  solver.add_argument("-roo", "--reload-on-overrun", action="store_true", help=f"Reload page on captcha overrun event.")
  solver.add_argument("-sll", "--solver-log-level", type=int, default=logging.INFO, metavar="N", help=f"TurnstileSolver log level. Default: {logging.INFO}. CRITICAL = 50, FATAL = CRITICAL, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0")

  # Server
  server = parser.add_argument_group("Server")
  server.add_argument("--host", default=c.HOST, help=f"Local host address. Default: {c.HOST}.")
  server.add_argument("--port", type=positive_integer, metavar="N", default=c.PORT, help=f"Local port. Default: {c.PORT}.")
  server.add_argument("-s", "--secret", default=c.SECRET, help=f"Server secret. Default: {c.SECRET}.")
  server.add_argument("-lal", "--log-access-logs", action="store_true", help=f"Log server access logs.")
  server.add_argument("-svll", "--server-log-level", type=int, default=logging.INFO, metavar="N", help=f"TurnstileSolverServer log level. Default: {logging.INFO}")
  server.add_argument("-ife", "--ignore-food-events", action="store_true", help=f"Do not log CAPTCHA foot events when server log level is DEBUG or below.")

  parser.add_argument("-p", "--production", action="store_true", help=f"Whether the project is running in a production environment or on a resource-constrained server, such as one that spins down during periods of inactivity.")
  parser.add_argument("-nn", "--no-ngrok", action="store_true", help=f"Do not use ngrok for keeping server alive on production.")
  parser.add_argument("-ncomp", "--no-computations", action="store_true", help=f"Do not simulate intensive computations for keeping server alive on production.")
  parser.add_argument("--headless", action="store_true", help=f"Open browser in headless mode. [#ffc800]WARNING[/]: This feature has never worked so far, captcha always fail! It's here only in case it works on future version of Playwright.")

  # Miscellaneous Options
  misc = parser.add_argument_group("Miscellaneous")
  misc.add_argument("-h", "--help", action="help", default=argparse.SUPPRESS, help='Show this help message.')
  misc.add_argument("-v", "--version", action='version', version=f'{__pname__} v{__version__}', help="Show version and exit.")


  return parser.parse_args()


def _add_help_custom_highlights():
  from rich.default_styles import DEFAULT_STYLES
  CustomRichHelpFormatter.styles["argparse.args"] = "#00FFFF"
  # Highlight rich.highlighter.ReprHighlighter
  CustomRichHelpFormatter.styles |= {f"argparse.{key.split('.')[1]}": val for key, val in DEFAULT_STYLES.items() if key.startswith('repr.')}
  CustomRichHelpFormatter.console = _console
  CustomRichHelpFormatter.highlights.extend(SolverConsoleHighlighter.highlights)


def _start_ngrok_tunnel() -> NgrokTunnel:
  # Set auth-token
  ngrok.set_auth_token(c.NGROK_TOKEN)

  # Kill active sessions if any
  ngrok.kill()

  tunnel: NgrokTunnel = ngrok.connect(str(c.PORT), "http")
  logger.info(tunnel)
  return tunnel


def _keep_server_alive(
    use_ngrok: bool = True,
    perform_computations: bool = True,
    ngrok_url: str | None = None,
    secret: str = c.SECRET,
):

  if not (use_ngrok or perform_computations):
    raise RuntimeError("You must either use Ngrok, perform computations, or both to keep server alive")

  def withNgrok():
    time.sleep(10)
    while True:
      response = requests.get(ngrok_url, headers={"ngrok-skip-browser-warning": "whatever", "secret": secret})
      response.raise_for_status()
      time.sleep(random.uniform(10, 30))

  def withComputations():
    while True:
      simulate_intensive_task(5000, 10000)
      time.sleep(random.uniform(0.01, 0.5))

  try:
    threads = []
    if use_ngrok:
      threads.append(t := Thread(target=withNgrok, daemon=True))
      t.start()
    if perform_computations:
      threads.append(t := Thread(target=withComputations, daemon=True))
      t.start()
    for t in threads:
      t.join()
  except (SystemExit, KeyboardInterrupt):
    pass
  except Exception as e:
    logger.error(f"keep_it_breathing interrupted with exception: {e}")


async def run_server(
    # Production
    production: bool = False,
    use_ngrok: bool = True,
    perform_computations: bool = True,
    max_contexts: int = c.MAX_CONTEXTS,
    max_pages_per_context: int = c.MAX_PAGES_PER_CONTEXT,
    single_browser_instance: bool = False,
    proxy_provider: ProxyProvider | None = None,

    console: SolverConsole | None = SolverConsole(),

    # TurnstileSolverServer
    host: str = c.HOST,
    port: int = c.PORT,
    disable_access_logs: bool = True,
    ignore_food_events: bool = False,
    server_log_level: int | str = logging.INFO,
    secret: str = c.SECRET,

    # TurnstileSolver
    page_load_timeout: float = c.PAGE_LOAD_TIMEOUT,
    browser_position: tuple[int, int] = c.BROWSER_POSITION,
    browser_executable_path: str | Path | None = None,
    reload_page_on_captcha_overrun_event: bool = False,
    max_attempts: int = c.MAX_ATTEMPTS_TO_SOLVE_CAPTCHA,
    attempt_timeout: int = c.CAPTCHA_ATTEMPT_TIMEOUT,
    headless: bool = False,
    solver_log_level: int | str = logging.INFO,
    proxy: Proxy | None = None,
    browser_args: list[str] | None = None,
):
  server = TurnstileSolverServer(
    host=host,
    port=port,
    secret=secret,
    disable_access_logs=disable_access_logs,
    turnstile_solver=None,
    on_shutting_down=None,
    console=console,
    log_level=server_log_level,
    ignore_food_events=ignore_food_events,
  )

  solver = TurnstileSolver(
    server=server,
    page_load_timeout=page_load_timeout,
    browser_position=browser_position,
    browser_executable_path=browser_executable_path,
    reload_page_on_captcha_overrun_event=reload_page_on_captcha_overrun_event,
    max_attempts=max_attempts,
    attempt_timeout=attempt_timeout,
    headless=headless,
    console=console,
    log_level=solver_log_level,
    proxy=proxy,
    browser_args=browser_args,
  )
  server.solver = solver
  await solver.server.create_browser_context_pool(
    max_contexts=max_contexts,
    max_pages_per_context=max_pages_per_context,
    single_instance=single_browser_instance,
    proxy_provider=proxy_provider,
  )

  try:
    # Keep it breathing
    if production:
      ngrok_url = _start_ngrok_tunnel().public_url if use_ngrok else None
      t = Process(
        target=_keep_server_alive,
        args=(use_ngrok, perform_computations, ngrok_url, secret),
        daemon=True,
      )
      t.start()

    # Start server
    await solver.server.run(debug=True)
  except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
    pass


async def main():

  dotenv.load_dotenv()

  traceback.install(
    show_locals=True,
    console=_console,
  )

  # Route hypercorn.error logs to __main__ logger
  logging.getLogger("hypercorn.error")._log = logger._log
  logging.getLogger("faker").setLevel(logging.WARNING)

  init_logger(
    console=_console,
    level=logging.INFO,
    handler_level=logging.NOTSET,
    force=True,
  )

  _add_help_custom_highlights()

  args = _parse_arguments()

  logging.root.setLevel(args.log_level)

  if not c.PROJECT_HOME_DIR.exists():
    c.PROJECT_HOME_DIR.mkdir(parents=True)

  # Register file logger
  if not args.no_file_logs:
    logging.root.addHandler(get_file_handler(c.PROJECT_HOME_DIR / 'logs.log'))

  if args.production and (args.no_ngrok and args.no_computations):
    logger.error("For keeping it alive you must either use Ngrok, perform computations, or both")
    return

  # Load global proxy
  if args.proxy_server:
    username = load_proxy_param(args.proxy_username)
    password = load_proxy_param(args.proxy_password)
    proxy = Proxy(args.proxy_server, username, password)
    logger.debug(f"Global proxy server loaded. Server: '{proxy.server}'")
  else:
    proxy = None

  if args.proxies:
    if not Path(args.proxies).is_file():
      logger.error(f"File: '{args.proxies}', does not exist")
      return
    proxyProvider = ProxyProvider(args.proxies)
    proxyProvider.load()
  else:
    proxyProvider = None

  await run_server(
    # Production
    production=args.production,
    use_ngrok=not args.no_ngrok,
    perform_computations=not args.no_computations,
    max_contexts=args.max_contexts,
    max_pages_per_context=args.max_pages,
    single_browser_instance=not args.multiple_browser_instances,
    proxy_provider=proxyProvider,

    # TurnstileSolverServer
    host=args.host,
    port=args.port,
    disable_access_logs=not args.log_access_logs,
    ignore_food_events=args.ignore_food_events,
    console=_console,
    server_log_level=args.server_log_level,
    secret=args.secret,

    # TurnstileSolver
    page_load_timeout=args.page_load_timeout,
    browser_position=args.browser_position,
    browser_executable_path=args.browser_executable_path,
    reload_page_on_captcha_overrun_event=args.reload_on_overrun,
    max_attempts=args.max_attempts,
    attempt_timeout=args.captcha_timeout,
    headless=args.headless,
    solver_log_level=args.solver_log_level,
    proxy=proxy,
    browser_args=args.browser_args,
  )


def main_cli():
  asyncio.run(main())


if __name__ == '__main__':
  asyncio.run(main())
