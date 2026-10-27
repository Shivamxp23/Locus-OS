"""
SPEC §7.1-7.9 & §27.7: Locus Display and Dashboard Subsystem.
"""
from __future__ import annotations

from sidecar.display.dashboard import (
    DashboardState,
    LocusDashboardRenderer,
    TUIDashboardEngine,
)
from sidecar.display.excalidraw_builder import (
    ExcalidrawDiagramBuilder,
    assemble_excalidraw_doc,
    compute_dag_layout,
    create_arrow,
    create_rectangle,
    extract_graph_from_spec,
    format_excalidraw_obsidian_wrapper,
    slugify,
)

__all__ = [
    "DashboardState",
    "LocusDashboardRenderer",
    "TUIDashboardEngine",
    "ExcalidrawDiagramBuilder",
    "assemble_excalidraw_doc",
    "compute_dag_layout",
    "create_arrow",
    "create_rectangle",
    "extract_graph_from_spec",
    "format_excalidraw_obsidian_wrapper",
    "slugify",
]
