"""Locus Code Graph Analysis (§29.6).

Extracts and maintains symbol, import, call, and inheritance dependencies across
codebases to calculate impact radiuses, detect cycles, and inform smart agent context.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Set, Optional


class SymbolKind(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    IMPORT = "import"


@dataclass
class CodeSymbolNode:
    name: str
    kind: SymbolKind
    file_path: str
    line_number: int
    docstring: Optional[str] = None
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "docstring": self.docstring,
            "references": self.references,
        }


class CodeDependencyGraph:
    """Directed dependency graph representing structural relationships in code."""

    def __init__(self):
        self.nodes: Dict[str, CodeSymbolNode] = {}
        self.edges: Dict[str, Set[str]] = {}  # source -> set of targets (dependencies)
        self.reverse_edges: Dict[str, Set[str]] = {}  # target -> set of sources (dependents)

    def add_node(self, node: CodeSymbolNode) -> None:
        self.nodes[node.name] = node
        if node.name not in self.edges:
            self.edges[node.name] = set()
        if node.name not in self.reverse_edges:
            self.reverse_edges[node.name] = set()

    def add_dependency(self, source_name: str, target_name: str) -> None:
        if source_name not in self.edges:
            self.edges[source_name] = set()
        if target_name not in self.reverse_edges:
            self.reverse_edges[target_name] = set()

        self.edges[source_name].add(target_name)
        self.reverse_edges[target_name].add(source_name)

    def parse_python_source(self, file_path: str, source_code: str) -> List[CodeSymbolNode]:
        tree = ast.parse(source_code)
        extracted: List[CodeSymbolNode] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                sym = CodeSymbolNode(
                    name=node.name,
                    kind=SymbolKind.CLASS,
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node),
                )
                self.add_node(sym)
                extracted.append(sym)
                # Bases as dependencies
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self.add_dependency(node.name, base.id)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                sym = CodeSymbolNode(
                    name=node.name,
                    kind=SymbolKind.FUNCTION,
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node),
                )
                self.add_node(sym)
                extracted.append(sym)

        return extracted

    def get_impact_radius(self, symbol_name: str, max_depth: int = 3) -> Set[str]:
        """Calculates all symbols transitively impacted if symbol_name changes."""
        impacted: Set[str] = set()
        frontier = {symbol_name}

        for _ in range(max_depth):
            next_frontier = set()
            for cur in frontier:
                dependents = self.reverse_edges.get(cur, set())
                for dep in dependents:
                    if dep not in impacted:
                        impacted.add(dep)
                        next_frontier.add(dep)
            frontier = next_frontier
            if not frontier:
                break

        return impacted

    def detect_cycles(self) -> List[List[str]]:
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(node: str):
            visited[node] = 1
            path.append(node)

            for neighbor in self.edges.get(node, set()):
                state = visited.get(neighbor, 0)
                if state == 1:
                    idx = path.index(neighbor)
                    cycles.append(list(path[idx:]))
                elif state == 0:
                    dfs(neighbor)

            path.pop()
            visited[node] = 2

        for n in list(self.nodes.keys()):
            if visited.get(n, 0) == 0:
                dfs(n)

        return cycles
