# -*- mode: python ; coding: utf-8 -*-
import logging
import asyncio
import os

import pytest
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from turnstile_solver.constants import HOST, PORT, SECRET
from turnstile_solver.solver import TurnstileSolver
from turnstile_solver.solver_console import SolverConsole
from turnstile_solver.turnstile_solver_server import TurnstileSolverServer

host = HOST
port = PORT


@pytest.fixture
def server(console: SolverConsole) -> TurnstileSolverServer:

  server = TurnstileSolverServer(
    host=HOST,
    port=PORT,
    secret=SECRET,
    console=console,
    log_level=logging.DEBUG,
    disable_access_logs=True,
    ignore_food_events=True,
    turnstile_solver=None,
    on_shutting_down=None,
  )

  return server


@pytest.fixture
def solver(server: TurnstileSolverServer) -> TurnstileSolver:
  EXECUTABLE_PATH = Path.home() / "AppData/Local/ms-playwright/chromium-1155/chrome-win/chrome.exe"

  proxyServer = os.environ.get('PROXY_SERVER')
  proxyUsername = os.environ.get('PROXY_USERNAME')
  proxyPassword = os.environ.get('PROXY_PASSWORD')

  s = TurnstileSolver(
    console=server.console,
    log_level=logging.DEBUG,
    page_load_timeout=60 * 1.5,
    reload_page_on_captcha_overrun_event=False,
    server=server,
    browser_position=None,
    browser_executable_path=EXECUTABLE_PATH,
    headless=False,
    proxy_server=proxyServer,
    proxy_username=proxyUsername,
    proxy_password=proxyPassword,
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


# TODO: Update
# async def test_server(solver: TurnstileSolver):
#   await solver.server.create_page_pool()
#   solver.max_attempts = 5
#   solver.attempt_timeout = 30
#   await solver.server.run(debug=True)


def _get_token(
    server_url: str,
    site_url: str,
    site_key: str,
):

  url = f"{server_url}/solve"

  headers = {
    'ngrok-skip-browser-warning': '_',
    'secret': 'jWRN7DH6',
    'Content-Type': 'application/json'
  }

  json_data = {
    "site_url": site_url,
    "site_key": site_key
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


def test_get_token(logger: logging.Logger):

  server_url = "http://127.0.0.1:8088"
  # server_url = "https://d8e6-35-185-23-87.ngrok-free.app"

  site_url, site_key = "https://spotifydown.com", "0x4AAAAAAAByvC31sFG0MSlp"
  # site_url, site_key = "https://bypass.city/", "0x4AAAAAAAGzw6rXeQWJ_y2P"

  requestCount = 1

  with ThreadPoolExecutor(max_workers=min(32, requestCount)) as executor:
    futures = []
    for _ in range(requestCount):
      future = executor.submit(
        _get_token,
        server_url,
        site_url,
        site_key,
      )
      futures.append(future)

    for future in as_completed(futures):
      try:
        future.result()
      except Exception as e:
        logging.error(f"Thread failed with error: {str(e)}")
