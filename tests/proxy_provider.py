# -*- mode: python ; coding: utf-8 -*-
from turnstile_solver.proxy_provider import ProxyProvider
from pytest import fixture
from rich.pretty import pprint


@fixture
def provider() -> ProxyProvider:
  return ProxyProvider(r'D:\cmd\proxies.txt')


def test_proxy_provider(provider: ProxyProvider):
  provider.load()
  pprint(provider.proxies, indent_guides=False)
