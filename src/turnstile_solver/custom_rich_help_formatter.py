# -*- mode: python ; coding: utf-8 -*-
from rich.console import RenderableType
from rich_argparse import RichHelpFormatter


class CustomRichHelpFormatter(RichHelpFormatter):
  def add_renderable(self, renderable: RenderableType) -> None:
    # from rich.padding import Padding
    # renderable = Padding.indent(renderable, self._current_indent)
    self._current_section.rich_items.append(renderable)
