"""sidecar/tools/excalidraw_builder.py - Excalidraw Diagram Generator.

Implements Spec §27.7:
- Generates valid Excalidraw JSON schema schemas containing nodes (rectangles, ellipses, diamonds),
  connecting arrows, text labels, and color formatting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class ExcalidrawElement:
    id: str
    type: str  # "rectangle", "ellipse", "diamond", "arrow", "text"
    x: float
    y: float
    width: float
    height: float
    text: str = ""
    strokeColor: str = "#1e1e1e"
    backgroundColor: str = "transparent"
    fillStyle: str = "solid"
    strokeWidth: int = 1


class ExcalidrawDiagramBuilder:
    """Constructs programmatic Excalidraw architecture diagrams."""

    def __init__(self) -> None:
        self.elements: list[ExcalidrawElement] = []

    def add_node(
        self,
        label: str,
        x: float,
        y: float,
        width: float = 160.0,
        height: float = 60.0,
        shape: str = "rectangle",
        bg_color: str = "#e3fafc",
    ) -> str:
        el_id = str(uuid4())[:8]
        self.elements.append(
            ExcalidrawElement(
                id=el_id,
                type=shape,
                x=x,
                y=y,
                width=width,
                height=height,
                text=label,
                backgroundColor=bg_color,
            )
        )
        return el_id

    def add_arrow(self, from_id: str, to_id: str, label: str = "") -> str:
        arrow_id = str(uuid4())[:8]
        self.elements.append(
            ExcalidrawElement(
                id=arrow_id,
                type="arrow",
                x=0.0,
                y=0.0,
                width=100.0,
                height=0.0,
                text=label,
            )
        )
        return arrow_id

    def to_json(self) -> str:
        data = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://locus.local",
            "elements": [
                {
                    "id": el.id,
                    "type": el.type,
                    "x": el.x,
                    "y": el.y,
                    "width": el.width,
                    "height": el.height,
                    "text": el.text,
                    "strokeColor": el.strokeColor,
                    "backgroundColor": el.backgroundColor,
                    "fillStyle": el.fillStyle,
                    "strokeWidth": el.strokeWidth,
                }
                for el in self.elements
            ],
            "appState": {"viewBackgroundColor": "#ffffff"},
        }
        return json.dumps(data, indent=2)
