import logging
from pathlib import Path

from turnstile_solver.proxy import Proxy

logger = logging.getLogger(__name__)


class ProxyProvider:
  def __init__(self, proxies_fp: str | Path):
    self.proxies_fp = proxies_fp
    self._index = 0
    self.proxies: list[Proxy] = []

  def get(self) -> Proxy | None:
    if not self.proxies:
      return
    proxy = self.proxies[self._index]
    self._index = (self._index + 1) % len(self.proxies)
    return proxy

  def load(self):
    with open(self.proxies_fp, 'rt') as f:
      proxyCount = 0
      for line in f.readlines():
        if not (line := line.strip()) or line.startswith('#'):
          continue
        parts = line.split('@')
        server = parts[0]
        if len(parts) > 1:
          username, password = parts[1].split(':')
        else:
          username = password = None
        self.proxies.append(Proxy(server, username, password))
        proxyCount += 1
      logger.info(f"{proxyCount} proxies loaded from '{self.proxies_fp}'")

  def __repr__(self) -> str:
    return str(self.proxies)
