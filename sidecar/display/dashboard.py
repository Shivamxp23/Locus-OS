"""Locus Terminal Dashboard & TUI Specification (§7.1-7.9, §30.8, §30.11).

Real-time terminal user interface that renders faction balance meters, active subagents,
context memory headroom, model token velocities, and interactive status bars.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DashboardState:
    active_model: str = "claude-3-5-sonnet"
    faction_distribution: Dict[str, float] = field(default_factory=lambda: {
        "Career": 0.40,
        "Health": 0.25,
        "Learning": 0.20,
        "Personal": 0.15,
    })
    running_subagents_count: int = 0
    token_usage_total: int = 0
    context_tokens_used: int = 15400
    context_token_limit: int = 128000
    recent_notifications: List[str] = field(default_factory=list)

    def get_context_headroom_pct(self) -> float:
        return max(0.0, 100.0 - (self.context_tokens_used / self.context_token_limit * 100.0))


class LocusTUIDashboard:
    """Renders ANSI / Curses formatted terminal status widgets."""

    def __init__(self):
        self.state = DashboardState()

    def update_metrics(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self.state, k):
                setattr(self.state, k, v)

    def render_faction_bar(self, width: int = 40) -> str:
        segments = []
        for faction, pct in self.state.faction_distribution.items():
            bar_len = int(round(pct * width))
            char = faction[0].upper()
            segments.append(char * bar_len)
        bar_str = "".join(segments)
        return f"[{bar_str.ljust(width, ' ')}]"

    def render_status_screen(self) -> str:
        bar = self.render_faction_bar(width=30)
        headroom = self.state.get_context_headroom_pct()
        return (
            "╔════════════════════════ LOCUS OS DASHBOARD ════════════════════════╗\n"
            f"║ Model: {self.state.active_model:<20} Subagents: {self.state.running_subagents_count:<6} Context: {headroom:5.1f}% free ║\n"
            f"║ Factions: {bar:<35} Tokens: {self.state.token_usage_total:<8} ║\n"
            "╚════════════════════════════════════════════════════════════════════╝\n"
        )
