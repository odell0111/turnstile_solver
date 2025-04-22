# -*- mode: python ; coding: utf-8 -*-
import json
import logging
import re

_PORT_RE = re.compile(r':\d+$')

logger = logging.getLogger(__name__)


class Proxy:
  def __init__(self,
               server: str,
               username: str | None,
               password: str | None,
               ):
    self.server = server

    if bool(username) ^ bool(password):
      raise ValueError(f'Username and password both must be specified. Username: {username}. Password: {password}')

    self.username = username
    self.password = password

    if not _PORT_RE.search(server):
      logger.warning("No proxy port specified")

  def dict(self):
    p = {
      'server': self.server,
      'bypass': '127.0.0.1, localhost',
    }
    if self.username:
      p['username'] = self.username
      p['password'] = self.password
    return p

  def __repr__(self) -> str:
    return json.dumps(self.dict(), indent=2)
