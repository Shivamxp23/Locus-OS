"""
SPEC §7.1-7.9: Terminal Interface & Native @earendil-works/pi-tui Augmentation (F-0030).
Implements DashboardState, 3-column footer formatter, and dashboard engine.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
from typing import Any, Dict, Optional

import sidecar.config as config

logger = logging.getLogger(__name__)


@dataclass
class DashboardState:
    """
    SPEC §7.1-7.9 lines 5840-5858:
    Dashboard State capturing Life OS DCS, operating mode, active faction,
    graph memory nodes/edges, LiveSync status, sidecar latency, and active model.
    """
    dcs: float = 5.0
    mode: str = "NORMAL"
    active_faction: str = "Leverage"
    neo4j_nodes: int = 0
    neo4j_edges: int = 0
    livesync_status: str = "OK"
    sidecar_latency_ms: int = 5
    model_name: str = "claude-3-7-sonnet"
    extra_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DashboardState:
        return cls(
            dcs=float(data.get("dcs", 5.0)),
            mode=str(data.get("mode", "NORMAL")),
            active_faction=str(data.get("active_faction", "Leverage")),
            neo4j_nodes=int(data.get("neo4j_nodes", 0)),
            neo4j_edges=int(data.get("neo4j_edges", 0)),
            livesync_status=str(data.get("livesync_status", "OK")),
            sidecar_latency_ms=int(data.get("sidecar_latency_ms", 5)),
            model_name=str(data.get("model_name", "claude-3-7-sonnet")),
            extra_metrics=data.get("extra_metrics") or {},
        )


class LocusDashboardRenderer:
    """
    SPEC §7.1-7.9 lines 5840-5858:
    Renderer for 3-column TUI footer widget and status dashboard.
    Left: Life OS DCS & Mode | Center: Graph Memory Count | Right: Sidecar Status & Model
    """

    @staticmethod
    def format_three_column_row(left: str, center: str, right: str, width: int = 80) -> str:
        """
        Format left, center, right text chunks across terminal width.
        Ensures clean separation and only truncates when total exceeds width.
        """
        if width <= 0:
            return f"{left} | {center} | {right}"

        total_len = len(left) + len(center) + len(right)
        if total_len + 2 <= width:
            available_spaces = width - total_len
            pad1 = max(1, available_spaces // 2)
            pad2 = max(1, available_spaces - pad1)
            return f"{left}{' ' * pad1}{center}{' ' * pad2}{right}"

        if total_len <= width:
            return f"{left} {center} {right}"

        # Proportional budget
        avail = max(10, width - 2)
        l_ratio = len(left) / total_len
        c_ratio = len(center) / total_len
        l_len = max(8, int(avail * l_ratio))
        c_len = max(8, int(avail * c_ratio))
        r_len = max(8, avail - l_len - c_len)

        l_str = left[:l_len]
        c_str = center[:c_len]
        r_str = right[:r_len]
        return f"{l_str} {c_str} {r_str}"

    @classmethod
    def render_footer(cls, state: DashboardState, width: int = 80) -> str:
        """
        SPEC §7.1-7.9 lines 5849-5857:
        left_col = f"DCS:{state.dcs} [{state.mode}] Faction:{state.active_faction}"
        center_col = f"Mem:{state.neo4j_nodes}n / {state.neo4j_edges}e | LiveSync:{state.livesync_status}"
        right_col = f"Sidecar:{state.sidecar_latency_ms}ms | {state.model_name}"
        """
        left_col = f"DCS:{state.dcs:.1f} [{state.mode}] Faction:{state.active_faction}"
        center_col = f"Mem:{state.neo4j_nodes}n / {state.neo4j_edges}e | LiveSync:{state.livesync_status}"
        right_col = f"Sidecar:{state.sidecar_latency_ms}ms | {state.model_name}"
        return cls.format_three_column_row(left_col, center_col, right_col, width=width)

    @classmethod
    def render_full_dashboard(cls, state: DashboardState, width: int = 80) -> str:
        """Format an expanded terminal dashboard status panel."""
        border = "=" * max(width, 40)
        lines = [
            border,
            f" LOCUS OS DASHBOARD :: STATE MONITOR".center(width),
            border,
            f" [LIFE OS]",
            f"   Dynamic Capacity Score (DCS) : {state.dcs:.2f}",
            f"   Current Operating Mode       : {state.mode}",
            f"   Active Faction               : {state.active_faction}",
            "",
            f" [GRAPH MEMORY & SYNC]",
            f"   Neo4j Entity Nodes           : {state.neo4j_nodes}",
            f"   Neo4j Relationship Edges     : {state.neo4j_edges}",
            f"   Obsidian LiveSync Status     : {state.livesync_status}",
            "",
            f" [RUNTIME INFRASTRUCTURE]",
            f"   Sidecar Heartbeat Latency    : {state.sidecar_latency_ms} ms",
            f"   Active LLM Provider/Model    : {state.model_name}",
            border,
            f" Footer Preview: {cls.render_footer(state, width)}",
            border,
        ]
        return "\n".join(lines)


class TUIDashboardEngine:
    """
    SPEC §7.1-7.9:
    Coordinates dashboard state gathering, sidecar metric polling, and layout generation.
    """

    def __init__(self) -> None:
        self.cached_state = DashboardState()

    def update_state(self, state: DashboardState) -> None:
        self.cached_state = state

    def get_state(self) -> DashboardState:
        """
        Pull latest metrics or return cached state.
        Default values align with active configuration.
        """
        model_name = config.get("locus.providers.llm.model", "claude-3-7-sonnet")
        mode = config.get("locus.life_os.mode", self.cached_state.mode)
        faction = config.get("locus.life_os.active_faction", self.cached_state.active_faction)

        self.cached_state.model_name = model_name
        self.cached_state.mode = mode
        self.cached_state.active_faction = faction
        return self.cached_state

    def format_footer(self, state: Optional[DashboardState] = None, width: int = 80) -> str:
        st = state or self.get_state()
        return LocusDashboardRenderer.render_footer(st, width=width)

    def format_dashboard(self, state: Optional[DashboardState] = None, width: int = 80) -> str:
        st = state or self.get_state()
        return LocusDashboardRenderer.render_full_dashboard(st, width=width)
