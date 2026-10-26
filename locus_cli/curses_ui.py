"""
SPEC §7.1-7.9 / F-0030: Standalone Curses/Terminal Dashboard UI for Locus CLI.
Provides terminal monitoring interface with graceful headless/non-interactive fallback.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

from sidecar.display.dashboard import DashboardState, LocusDashboardRenderer

logger = logging.getLogger(__name__)


class CursesDashboard:
    """
    Terminal Curses Dashboard for Locus state monitoring.
    Can run in full curses mode or headless static snapshot mode.
    """

    def __init__(self, state: Optional[DashboardState] = None) -> None:
        self.state = state or DashboardState()
        self.renderer = LocusDashboardRenderer()

    def update_state(self, state: DashboardState) -> None:
        self.state = state

    def render_snapshot(self, width: int = 80) -> str:
        """Render static snapshot string of dashboard for non-curses output."""
        return self.renderer.render_full_dashboard(self.state, width=width)

    def draw(self, stdscr: Any) -> None:
        """Draw dashboard onto a curses screen buffer."""
        try:
            import curses
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()
            lines = self.render_snapshot(width=max(max_x - 2, 40)).splitlines()
            for i, line in enumerate(lines[:max_y]):
                try:
                    stdscr.addstr(i, 0, line[:max_x])
                except curses.error:
                    pass
            stdscr.refresh()
        except ImportError:
            pass

    def run(self, headless: bool = True) -> int:
        """
        Run dashboard loop. In headless/test mode, prints snapshot and returns 0.
        """
        if headless or not sys.stdin.isatty():
            output = self.render_snapshot()
            print(output)
            return 0

        try:
            import curses

            def _curses_main(stdscr: Any) -> None:
                stdscr.nodelay(True)
                self.draw(stdscr)
                # Wait for any key or single refresh
                try:
                    stdscr.getch()
                except Exception:
                    pass

            curses.wrapper(_curses_main)
            return 0
        except Exception as e:
            logger.warning(f"Curses interface unavailable: {e}. Falling back to snapshot.")
            print(self.render_snapshot())
            return 0


def main() -> None:
    """Entry point for python -m locus_cli.curses_ui."""
    dash = CursesDashboard()
    dash.run(headless=False)


if __name__ == "__main__":
    main()
