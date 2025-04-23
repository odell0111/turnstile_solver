# -*- mode: python ; coding: utf-8 -*-
import asyncio
import logging
from collections import deque
from inspect import isawaitable

from typing import Callable, Any, Awaitable

logger = logging.getLogger(__name__)


class Pool:
  def __init__(self,
               size: int,
               item_getter: Callable[[], Any | Awaitable[Any]],
               ):
    self.size = size

    self._item_getter = item_getter
    self.in_use = []
    self._available: deque = deque()
    self._lock = asyncio.Lock()

  @property
  def is_full(self) -> bool:
    return len(self.in_use) == self.size

  async def get(self) -> Any:
    async with self._lock:
      # Check possible runtime error
      if len(self.in_use) > self.size:
        raise RuntimeError("len(self._in_use) is supposed to be less than self.size")
      # Wait for any item to be available
      if self.is_full:
        logger.debug("Waiting for a new item to be available")
        while self.is_full:
          await asyncio.sleep(0.1)
      # Get an item from available ones if any and put it in self._in_use list
      if len(self._available) > 0:
        self.in_use.append(item := self._available.popleft())
        return item
      # Then len(self._in_use) is less than self.max_size, so safely create a item page and put it in self._in_use list
      item = await self._get_item()
      self.in_use.append(item)
      logger.debug(f"New item '{item}' added to pool")
      return item

  async def put_back(self, item: Any):
    # Do nothing if item is available
    if item in self._available:
      return

    # Check possible runtime error
    if len(self._available) >= self.size:
      raise RuntimeError("len(self._available) is supposed to be less than self.size. Make sure to always call put_back() method only if get() method have been called previously")

    # Check possible runtime error again in which provided page may not have been fetched via get() method
    try:
      index = self.in_use.index(item)
    except ValueError:
      raise RuntimeError("The item provided seems not have been fetched via the get() method, and it is supposed to be this way. Make sure to always call put_back() method only if get() method have been called previously")
    logger.debug(f"Item '{item}' back on pool")
    self._available.append(self.in_use.pop(index))

  async def _get_item(self):
    item = self._item_getter()
    if isawaitable(item):
      item = await item
    return item
