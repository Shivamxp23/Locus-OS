"""sidecar/context/coding_context.py - Coding Context Engine (Repo Map, AST Index, Active Diff).

Implements Spec §6.3:
- Builds structural repository tree maps.
- Extracts symbol definitions from AST.
- Integrates active uncommitted git diffs into agent's prompt turn context.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SymbolSignature:
    name: str
    kind: str  # "class", "function", "async_function"
    line_number: int


@dataclass
class FileContextSummary:
    rel_path: str
    symbols: list[SymbolSignature] = field(default_factory=list)


class CodingContextEngine:
    """Extracts repo maps and symbol outlines for agent coding turns."""

    def __init__(self, root_path: Optional[str | Path] = None) -> None:
        self.root_path = Path(root_path or Path.cwd()).resolve()

    def extract_python_symbols(self, file_path: str | Path) -> list[SymbolSignature]:
        p = Path(file_path)
        if not p.is_file():
            return []
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            signatures = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    signatures.append(SymbolSignature(node.name, "class", node.lineno))
                elif isinstance(node, ast.FunctionDef):
                    signatures.append(SymbolSignature(node.name, "function", node.lineno))
                elif isinstance(node, ast.AsyncFunctionDef):
                    signatures.append(SymbolSignature(node.name, "async_function", node.lineno))
            return signatures
        except Exception:
            return []

    def build_repo_map(self, max_files: int = 15) -> list[FileContextSummary]:
        summaries: list[FileContextSummary] = []
        count = 0
        for py_file in self.root_path.glob("sidecar/**/*.py"):
            if count >= max_files:
                break
            rel = str(py_file.relative_to(self.root_path)).replace("\\", "/")
            syms = self.extract_python_symbols(py_file)
            summaries.append(FileContextSummary(rel_path=rel, symbols=syms))
            count += 1
        return summaries
