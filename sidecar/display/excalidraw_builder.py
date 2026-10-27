"""
SPEC §27.7 lines 7305-7378: Excalidraw MCP Skill (Visual Architecture Diagrams) (F-0063 / US-100).
Source: Excalidraw JSON Schema Spec + MCP Skill Protocol
Logic:
    Layout engine computing coordinate bounding boxes, arrow connector vectors,
    and shape styles; assembles valid .excalidraw vector diagram JSON from
    natural language system descriptions and writes directly into Obsidian
    under /vault/03-Resources/Diagrams/{output_filename}.excalidraw.md.
Off state:
    locus.tools.excalidraw.enabled / locus.display.excalidraw.enabled:
    when off, diagram generation is disabled or returns 503.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar import config

logger = logging.getLogger("locus.display.excalidraw")


def slugify(text: str) -> str:
    """Convert text into filesystem-safe filename slug."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[-\s]+", "-", clean).strip("-_")
    return clean[:80] or "untitled-diagram"


def create_rectangle(
    id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str = "",
    bg_color: str = "#e0f2fe",
) -> Dict[str, Any]:
    """
    SPEC §27.7 line 7319:
    FUNCTION create_rectangle(id, x, y, width, height, text, bg_color="#e0f2fe") -> Dict
    """
    return {
        "id": id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#1e293b",
        "backgroundColor": bg_color,
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3},
        "seed": 10423985,
        "version": 1,
        "versionNonce": 0,
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
        "text": text,
    }


def create_arrow(
    id: str,
    start_element_id: str,
    end_element_id: str,
    label: str = "",
    start_x: float = 0.0,
    start_y: float = 0.0,
    end_x: float = 100.0,
    end_y: float = 0.0,
) -> Dict[str, Any]:
    """
    SPEC §27.7 line 7331:
    FUNCTION create_arrow(id, start_element_id, end_element_id, label="") -> Dict
    """
    dx = end_x - start_x
    dy = end_y - start_y
    return {
        "id": id,
        "type": "arrow",
        "x": start_x,
        "y": start_y,
        "width": abs(dx) or 10.0,
        "height": abs(dy) or 10.0,
        "angle": 0,
        "strokeColor": "#475569",
        "backgroundColor": "transparent",
        "fillStyle": "hachure",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 2},
        "seed": 2048592,
        "version": 1,
        "versionNonce": 0,
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [dx, dy]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": start_element_id, "focus": 0, "gap": 1},
        "endBinding": {"elementId": end_element_id, "focus": 0, "gap": 1},
        "startArrowhead": None,
        "endArrowhead": "arrow",
        "label": label,
    }


def compute_dag_layout(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    x_spacing: float = 240.0,
    y_spacing: float = 140.0,
    node_w: float = 180.0,
    node_h: float = 70.0,
) -> Dict[str, Any]:
    """
    SPEC §27.7 line 7346:
    Compute Layout Coordinates (Layered DAG layout).
    """
    # Graph structure
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    in_deg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        u = e.get("source") or e.get("start")
        v = e.get("target") or e.get("end")
        if u in adj and v in in_deg:
            adj[u].append(v)
            in_deg[v] += 1

    # Topological layering
    layers: List[List[str]] = []
    current_layer = [n for n in in_deg if in_deg[n] == 0]
    if not current_layer and nodes:
        current_layer = [nodes[0]["id"]]

    assigned: Set[str] = set()
    while current_layer:
        layers.append(current_layer)
        assigned.update(current_layer)
        next_layer = []
        for u in current_layer:
            for v in adj.get(u, []):
                in_deg[v] -= 1
                if in_deg[v] <= 0 and v not in assigned and v not in next_layer:
                    next_layer.append(v)
        current_layer = next_layer

    # Add unvisited nodes (cycles or disconnected components)
    unvisited = [n["id"] for n in nodes if n["id"] not in assigned]
    if unvisited:
        layers.append(unvisited)

    # Position coordinates per layer
    positions: Dict[str, Tuple[float, float]] = {}
    elements: List[Dict[str, Any]] = []

    for layer_idx, layer in enumerate(layers):
        x = 100.0 + layer_idx * x_spacing
        for row_idx, node_id in enumerate(layer):
            y = 100.0 + row_idx * y_spacing
            positions[node_id] = (x, y)

    node_map = {n["id"]: n for n in nodes}
    for node_id, (x, y) in positions.items():
        node_info = node_map.get(node_id, {})
        text = node_info.get("label") or node_info.get("text") or node_id
        bg = node_info.get("bg_color") or "#e0f2fe"
        rect = create_rectangle(node_id, x, y, node_w, node_h, text=text, bg_color=bg)
        elements.append(rect)

    # Connect arrows
    arrow_counter = 1
    for e in edges:
        u = e.get("source") or e.get("start")
        v = e.get("target") or e.get("end")
        label = e.get("label", "")
        if u in positions and v in positions:
            ux, uy = positions[u]
            vx, vy = positions[v]
            # Center points
            start_x = ux + node_w
            start_y = uy + node_h / 2
            end_x = vx
            end_y = vy + node_h / 2
            arrow_id = f"arrow-{arrow_counter}"
            arrow_counter += 1
            arr = create_arrow(
                id=arrow_id,
                start_element_id=u,
                end_element_id=v,
                label=label,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
            )
            elements.append(arr)

    return {
        "elements": elements,
        "layers_count": len(layers),
        "nodes_count": len(positions),
        "edges_count": arrow_counter - 1,
    }


def assemble_excalidraw_doc(
    elements: List[Dict[str, Any]], background_color: str = "#ffffff"
) -> Dict[str, Any]:
    """
    SPEC §27.7 line 7349:
    Assemble Full Excalidraw Document JSON.
    """
    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "viewBackgroundColor": background_color,
            "gridSize": None,
        },
        "files": {},
    }


def format_excalidraw_obsidian_wrapper(doc: Dict[str, Any], title: str = "Architecture Diagram") -> str:
    """
    Format into canonical Obsidian Excalidraw plugin markdown format.
    """
    doc_json = json.dumps(doc, indent=2)
    return (
        f"---\n"
        f"excalidraw-plugin: parsed\n"
        f"tags: [\"#resource/diagram\", \"#excalidraw\"]\n"
        f"title: \"{title}\"\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"```json\n"
        f"{doc_json}\n"
        f"```\n"
    )


def extract_graph_from_spec(system_spec: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract components (nodes) and directed relationships (edges) from natural language
    or structured architecture descriptions.
    """
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    lines = system_spec.splitlines()
    for line in lines:
        stripped = line.strip().lstrip("-*# ")
        if not stripped:
            continue

        # Pattern: A -> B or A --> B or A connects to B
        arrow_match = re.search(r"(\w[\w\s-]*?)\s*(?:->|-->|connects to|calls|interacts with)\s*(\w[\w\s-]*)", stripped, re.IGNORECASE)
        if arrow_match:
            src = arrow_match.group(1).strip()
            tgt = arrow_match.group(2).strip()
            src_id = slugify(src)
            tgt_id = slugify(tgt)

            if src_id not in nodes:
                nodes[src_id] = {"id": src_id, "label": src, "bg_color": "#e0f2fe"}
            if tgt_id not in nodes:
                nodes[tgt_id] = {"id": tgt_id, "label": tgt, "bg_color": "#dbeafe"}

            edges.append({"source": src_id, "target": tgt_id, "label": ""})
            continue

        # Colon pattern: Module: description or Component: Target
        col_match = re.search(r"^(\w[\w\s-]*?)\s*:\s*(.*)$", stripped)
        if col_match:
            comp = col_match.group(1).strip()
            comp_id = slugify(comp)
            if comp_id not in nodes:
                nodes[comp_id] = {"id": comp_id, "label": comp, "bg_color": "#fef3c7"}

    # Default fallback nodes if none parsed
    if not nodes:
        words = [w for w in re.findall(r"\b[A-Za-z0-9_-]{3,}\b", system_spec) if w.lower() not in ("the", "and", "for", "with", "from")]
        node_names = words[:4] or ["Client", "Sidecar", "Vault", "Engine"]
        for idx, name in enumerate(node_names):
            nid = slugify(name)
            nodes[nid] = {"id": nid, "label": name, "bg_color": "#e0f2fe"}
            if idx > 0:
                prev_id = slugify(node_names[idx - 1])
                edges.append({"source": prev_id, "target": nid, "label": ""})

    return list(nodes.values()), edges


class ExcalidrawDiagramBuilder:
    """
    SPEC §27.7: Excalidraw MCP Skill layout & diagram synthesis engine.
    """

    SWITCH_KEY = "locus.tools.excalidraw.enabled"

    def is_enabled(self) -> bool:
        """Check subsystem off-switch."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def resolve_vault_path(self, custom_vault: Optional[Path] = None) -> Path:
        """Resolve base vault path."""
        if custom_vault:
            return custom_vault.resolve()
        cfg_vault = config.get("locus.vault.path")
        if cfg_vault:
            return Path(cfg_vault).resolve()
        return (config.get_locus_home() / "vault").resolve()

    def generate_diagram(
        self,
        system_spec: str,
        output_filename: str = "architecture_diagram",
        save_to_vault: bool = True,
        vault_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        SPEC §27.7 lines 7341-7362:
        Synthesize Excalidraw diagram document and write to vault.
        """
        if not self.is_enabled():
            return {
                "status": "DISABLED",
                "error": "Excalidraw diagram builder is disabled (locus.tools.excalidraw.enabled)",
                "status_code": 503,
            }

        if not system_spec or not system_spec.strip():
            return {
                "status": "ERROR",
                "error": "Empty system specification provided",
                "status_code": 400,
            }

        # 1. Extract nodes & edges
        nodes, edges = extract_graph_from_spec(system_spec)

        # 2. Compute DAG layout
        layout = compute_dag_layout(nodes, edges)

        # 3. Assemble document JSON
        doc = assemble_excalidraw_doc(layout["elements"])

        clean_slug = slugify(output_filename)
        markdown_wrapper = format_excalidraw_obsidian_wrapper(doc, title=output_filename)

        vault_file_str: Optional[str] = None
        if save_to_vault:
            base_vault = self.resolve_vault_path(vault_root)
            diag_dir = base_vault / "03-Resources" / "Diagrams"
            diag_dir.mkdir(parents=True, exist_ok=True)

            target_file = diag_dir / f"{clean_slug}.excalidraw.md"
            target_file.write_text(markdown_wrapper, encoding="utf-8")
            vault_file_str = str(target_file)

        return {
            "status": "SAVED",
            "path": vault_file_str,
            "filename": f"{clean_slug}.excalidraw.md",
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "elements_count": len(layout["elements"]),
            "document": doc,
            "status_code": 200,
        }

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""
        return {
            "subsystem_enabled": self.is_enabled(),
            "target_vault_dir": "03-Resources/Diagrams/",
            "excalidraw_version": 2,
        }
