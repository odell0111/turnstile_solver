from rich.console import Console
from rich.theme import Theme

from turnstile_solver.constants import CONSOLE_THEME_STYLES
from turnstile_solver.solver_console_highlighter import SolverConsoleHighlighter

MAX_CONSOLE_WIDTH = 200


class SolverConsole(Console):
  def __init__(self, *args, **kwargs):
    kwargs['theme'] = Theme(CONSOLE_THEME_STYLES)
    kwargs['highlighter'] = SolverConsoleHighlighter()
    super().__init__(*args, **kwargs)
    if isinstance(self.width, int) and self.width > MAX_CONSOLE_WIDTH:
      self.width = MAX_CONSOLE_WIDTH
