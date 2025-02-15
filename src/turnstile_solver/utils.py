import logging
import random
import time

from faker import Faker
from rich.logging import RichHandler

from .solver_console import SolverConsole

_faker = Faker(locale='en_US')


def init_logger(
    console=SolverConsole(),
    level=logging.INFO,
    handler_level=logging.NOTSET,
    force=False,
):
  richHandler = RichHandler(level=handler_level,
                            markup=True,
                            show_path=False,
                            log_time_format='[%X]',
                            console=console,
                            rich_tracebacks=True)
  # logging.root.addHandler(richHandler)
  logging.basicConfig(level=level,
                      format="%(message)s",
                      datefmt="[%X]",
                      force=force,
                      handlers=[richHandler])


def password(length: int | tuple[int, int] = (10, 15), special_chars: bool = False):
  return _faker.password(
    length=length if isinstance(length, int) else random.randint(*length),
    special_chars=special_chars
  )


def simulate_intensive_task(iterations=2500, complexity=10000):
  startTime = time.time()
  for _ in range(iterations):
    for _ in range(complexity):
      value = random.random() * complexity
      value **= 3
  return time.time() - startTime
