"""
SPEC §27.7 lines 7305-7378: Excalidraw Builder canonical sidecar tools location.
Re-exports from sidecar.display.excalidraw_builder.
"""
from __future__ import annotations

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
    "ExcalidrawDiagramBuilder",
    "assemble_excalidraw_doc",
    "compute_dag_layout",
    "create_arrow",
    "create_rectangle",
    "extract_graph_from_spec",
    "format_excalidraw_obsidian_wrapper",
    "slugify",
]
