import logging

import asyncio
import pytest
import requests

from ..constants import HOST, PORT, SECRET
from ..solver import TurnstileSolver
from ..solver_console import SolverConsole
from ..turnstile_solver_server import TurnstileSolverServer

host = HOST
port = PORT

logger = logging.getLogger(__name__)


@pytest.fixture
def server(console: SolverConsole) -> TurnstileSolverServer:

  server = TurnstileSolverServer(
    host=HOST,
    port=PORT,
    secret=c.SECRET,
    console=console,
    log_level=logging.DEBUG,
    disable_access_logs=True,
    turnstile_solver=None,
    on_shutting_down=None,
  )

  return server


@pytest.fixture
def solver(server: TurnstileSolverServer) -> TurnstileSolver:
  EXECUTABLE_PATH = r"C:\Users\odell\AppData\Local\ms-playwright\chromium-1148\chrome-win\chrome.exe"
  # EXECUTABLE_PATH = r"C:\Users\odell\AppData\Local\ms-playwright\chromium_headless_shell-1148\chrome-win\headless_shell.exe"
  # EXECUTABLE_PATH = r"C:\Program Files\Chromium\Application\chrome.exe"
  # EXECUTABLE_PATH = None

  s = TurnstileSolver(
    console=server.console,
    log_level=logging.DEBUG,
    page_load_timeout=60 * 1.5,
    reload_page_on_captcha_overrun_event=False,
    server=server,
    browser_position=None,
    browser_executable_path=EXECUTABLE_PATH,
    headless=False,
  )
  server.solver = s
  return s


async def test_solve(solver: TurnstileSolver):

  # siteUrl, siteKey = "https://2captcha.com/demo/cloudflare-turnstile", "0x1AAAAAAAAkg0s2VIOD34y5"
  siteUrl, siteKey = "https://spotifydown.com/", "0x4AAAAAAAByvC31sFG0MSlp"

  async with asyncio.TaskGroup() as tg:
    serverTask = tg.create_task(solver.server.run(debug=True), name="server_task")

    async def _solve():
      await solver.server.wait_for_server()
      result = await solver.solve(
        site_url=siteUrl,
        site_key=siteKey,
        attempts=5,
        timeout=30,
        page=False,
        about_blank_on_finish=False,
      )
      serverTask.cancel()
      return result

    tokenTask = tg.create_task(_solve(), name="solve_task")
  if r := tokenTask.result():
    print("TOKEN", r.token)


async def test_server(solver: TurnstileSolver):
  await solver.server.create_page_pool()
  solver.max_attempts = 5
  solver.attempt_timeout = 30
  await solver.server.run(debug=True)

def test_get_token():

  SERVER_URL = "http://127.0.0.1:8088"

  url = f"{SERVER_URL}/solve"

  headers = {
    'ngrok-skip-browser-warning': '_',
    'secret': 'jWRN7DH6',
    'Content-Type': 'application/json'
  }

  json_data = {
    "site_url": "https://spotifydown.com",
    "site_key": "0x4AAAAAAAByvC31sFG0MSlp"
  }

  response = requests.get(
    url=url,
    headers=headers,
    json=json_data,
  )

  response.raise_for_status()
  
  data = response.json()
  token = data['token']
  elapsed = data['elapsed']
  print(f"Token: {token}\n"
        f"Elapsed: {elapsed}")