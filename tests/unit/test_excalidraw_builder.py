"""
Unit tests for Excalidraw MCP Skill (Visual Architecture Diagrams) (F-0063 / US-100).
"""
import json
from pathlib import Path
import pytest
from typing import Any, Dict, List, Optional

from sidecar import config
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
from sidecar.providers.excalidraw import (
    BaseDiagramGeneratorProvider,
    DefaultDiagramGeneratorProvider,
    DiagramGeneratorProvider,
)


def test_create_rectangle_element():
    """
    SPEC §27.7 line 7319: "FUNCTION create_rectangle(id, x, y, width, height, text, bg_color=\"#e0f2fe\") -> Dict"
    """
    rect = create_rectangle(
        id="node-1",
        x=100.0,
        y=150.0,
        width=180.0,
        height=70.0,
        text="Sidecar Engine",
        bg_color="#e0f2fe",
    )
    assert rect["id"] == "node-1"
    assert rect["type"] == "rectangle"
    assert rect["x"] == 100.0
    assert rect["y"] == 150.0
    assert rect["width"] == 180.0
    assert rect["height"] == 70.0
    assert rect["backgroundColor"] == "#e0f2fe"
    assert rect["strokeColor"] == "#1e293b"
    assert rect["roundness"] == {"type": 3}
    assert rect["text"] == "Sidecar Engine"


def test_create_arrow_element():
    """
    SPEC §27.7 line 7331: "FUNCTION create_arrow(id, start_element_id, end_element_id, label=\"\") -> Dict"
    """
    arrow = create_arrow(
        id="arrow-1",
        start_element_id="node-1",
        end_element_id="node-2",
        label="Dispatches Task",
        start_x=280.0,
        start_y=185.0,
        end_x=400.0,
        end_y=185.0,
    )
    assert arrow["id"] == "arrow-1"
    assert arrow["type"] == "arrow"
    assert arrow["startBinding"]["elementId"] == "node-1"
    assert arrow["endBinding"]["elementId"] == "node-2"
    assert arrow["label"] == "Dispatches Task"
    assert arrow["endArrowhead"] == "arrow"
    assert len(arrow["points"]) == 2


def test_compute_dag_layout():
    """
    SPEC §27.7 line 7346: "layout = compute_dag_layout(graph_def.nodes, graph_def.edges)"
    """
    nodes = [
        {"id": "api", "label": "FastAPI Client"},
        {"id": "service", "label": "Locus Service"},
        {"id": "db", "label": "Neo4j Graph"},
    ]
    edges = [
        {"source": "api", "target": "service", "label": "calls"},
        {"source": "service", "target": "db", "label": "queries"},
    ]

    layout = compute_dag_layout(nodes, edges)
    elements = layout["elements"]

    # 3 nodes + 2 arrows = 5 elements
    assert len(elements) == 5
    rects = [e for e in elements if e["type"] == "rectangle"]
    arrows = [e for e in elements if e["type"] == "arrow"]
    assert len(rects) == 3
    assert len(arrows) == 2

    # Check horizontal ordering (api -> service -> db)
    api_rect = next(r for r in rects if r["id"] == "api")
    srv_rect = next(r for r in rects if r["id"] == "service")
    db_rect = next(r for r in rects if r["id"] == "db")
    assert api_rect["x"] < srv_rect["x"] < db_rect["x"]


def test_assemble_excalidraw_doc_and_obsidian_wrapper():
    """
    SPEC §27.7 line 7349: "Assemble Full Excalidraw Document JSON"
    """
    rect = create_rectangle("n1", 10, 20, 100, 50, "Node")
    doc = assemble_excalidraw_doc([rect], background_color="#ffffff")

    assert doc["type"] == "excalidraw"
    assert doc["version"] == 2
    assert doc["source"] == "https://excalidraw.com"
    assert doc["appState"]["viewBackgroundColor"] == "#ffffff"
    assert len(doc["elements"]) == 1

    md = format_excalidraw_obsidian_wrapper(doc, title="Architecture Topology")
    assert "excalidraw-plugin: parsed" in md
    assert "# Architecture Topology" in md
    assert "```json" in md
    assert '"type": "excalidraw"' in md


def test_extract_graph_from_natural_language_spec():
    """
    SPEC §27.7 line 7344: "graph_def = call_plugin_llm(f\"Extract nodes and relationships from: {system_spec}\", schema=GraphDefSchema)"
    """
    spec = """
    Telegram Bot -> Message Router
    Message Router -> Life OS Service
    Life OS Service -> Vault Storage
    """
    nodes, edges = extract_graph_from_spec(spec)
    assert len(nodes) >= 4
    assert len(edges) >= 3
    edge_sources = [e["source"] for e in edges]
    assert any("telegram" in s for s in edge_sources)


def test_vault_persistence_diagrams(tmp_path):
    """
    SPEC §27.7 line 7356: "vault_file = f\"/vault/03-Resources/Diagrams/{output_filename}.excalidraw.md\""
    """
    builder = ExcalidrawDiagramBuilder()
    spec = "Ingestion Pipeline -> Knowledge Graph -> Vector Index"

    res = builder.generate_diagram(
        system_spec=spec,
        output_filename="System Knowledge Topology",
        save_to_vault=True,
        vault_root=tmp_path,
    )

    assert res["status"] == "SAVED"
    assert res["path"] is not None
    assert Path(res["path"]).exists()
    assert "03-Resources" in res["path"]
    assert "Diagrams" in res["path"]
    assert res["path"].endswith(".excalidraw.md")

    content = Path(res["path"]).read_text(encoding="utf-8")
    assert "excalidraw-plugin: parsed" in content
    assert '"type": "excalidraw"' in content


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.7 line 7370: "Swappable / off state: locus.tools.excalidraw.enabled"
    """
    builder = ExcalidrawDiagramBuilder()
    switch = builder.SWITCH_KEY

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert builder.is_enabled() is False

    res = builder.generate_diagram("A -> B")
    assert res["status"] == "DISABLED"
    assert res["status_code"] == 503


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.7 line 7370: "Provider Interface: DiagramGeneratorProvider"
    """
    provider = DefaultDiagramGeneratorProvider()
    switch = "locus.tools.excalidraw.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_gen = provider.generate_diagram("A -> B")
    assert res_gen.get("status_code") == 503
    assert res_gen.get("disabled") == switch

    res_st = provider.get_status()
    assert res_st.get("status_code") == 503
    assert res_st.get("disabled") == switch


def test_provider_swap_polymorphism():
    """
    SPEC §27.7 line 7370: "Provider Interface: DiagramGeneratorProvider"
    """
    class MockDiagramGeneratorProvider(BaseDiagramGeneratorProvider):
        @property
        def name(self) -> str:
            return "mock_diagram_generator"

        def is_feature_enabled(self):
            return True, "mock.switch"

        def generate_diagram(self, system_spec, output_filename="diagram", save_to_vault=True, vault_root=None):
            return {"status_code": 200, "status": "SAVED", "path": "/mock/diagram.excalidraw.md", "elements_count": 5}

        def get_status(self):
            return {"status_code": 200, "mock": True}

    provider: DiagramGeneratorProvider = MockDiagramGeneratorProvider()
    assert provider.name == "mock_diagram_generator"
    res = provider.generate_diagram("X -> Y")
    assert res["status_code"] == 200
    assert res["elements_count"] == 5
