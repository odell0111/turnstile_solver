# -*- mode: python ; coding: utf-8 -*-
from rich.highlighter import ReprHighlighter

_ORIGINAL_NUMBER_HIGHLIGHTER = r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)"


class SolverConsoleHighlighter(ReprHighlighter):
  _version_numbering_highlight = r"(\b(?P<version>v\d+\.\d+(?:\.\d*)*)\b)"
  ReprHighlighter.highlights[-1] = ReprHighlighter.highlights[-1] + '|' + _version_numbering_highlight

  highlights = ReprHighlighter.highlights + [
    r"\b(?P<author>OGM)\b",
    r"\b(?P<projectname>Turnstile Solver)\b",
    r"\b(?P<headless>headless)\b",  # highlight `text in backquotes` as syntax
  ]
