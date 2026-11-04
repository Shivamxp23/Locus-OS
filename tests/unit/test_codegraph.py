"""
Unit tests for Code Graph Analysis (SPEC §29.6 / F-0069 / US-107).
"""
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Tuple
import pytest

from sidecar.codegraph.analyzer import CodeGraphAnalyzer, DependencyGraph
from sidecar.providers.codegraph import BaseCodeGraphProvider, DefaultCodeGraphProvider
from sidecar import config


def test_scan_directory_discovers_source_files_and_ignores_excludes(tmp_path: Path):
    """SPEC §29.6 line 7690: "files = scan_directory(project_path, extensions=['.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go'], exclude=['node_modules', '.git', 'dist', 'build', '__pycache__'])" """
    # Setup test workspace
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("console.log('hi')", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("print('py')", encoding="utf-8")
    (tmp_path / "src" / "main.rs").write_text("fn main() {}", encoding="utf-8")
    (tmp_path / "src" / "server.go").write_text("package main", encoding="utf-8")
    (tmp_path / "src" / "notes.txt").write_text("text doc", encoding="utf-8")  # Non-code file

    # Excluded directories
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("module.exports = {}", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("bundled", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "app.cpython-311.pyc").write_text("bytecode", encoding="utf-8")

    analyzer = CodeGraphAnalyzer()
    files = analyzer.scan_directory(tmp_path)

    assert "src/index.ts" in files
    assert "src/app.py" in files
    assert "src/main.rs" in files
    assert "src/server.go" in files
    assert "src/notes.txt" not in files
    assert "node_modules/dep.js" not in files
    assert "dist/bundle.js" not in files
    assert "__pycache__/app.cpython-311.pyc" not in files


def test_extract_imports_python():
    """SPEC §29.6 line 7696: "Extract import/dependency relationships: imports = extract_imports(file)" """
    analyzer = CodeGraphAnalyzer()
    py_code = """
import os
import sys, math
from pathlib import Path
from sidecar.diagnostics.connectivity import ConnectivityChecker
from .utils import helper
"""
    imports = analyzer.extract_imports("test.py", content=py_code)
    assert "os" in imports
    assert "sys" in imports
    assert "math" in imports
    assert "pathlib" in imports
    assert "sidecar.diagnostics.connectivity" in imports
    assert ".utils" in imports


def test_extract_imports_typescript_and_javascript():
    """SPEC §29.6 line 7696: "Extract import/dependency relationships: imports = extract_imports(file)" """
    analyzer = CodeGraphAnalyzer()
    ts_code = """
import { ConnectivityClient } from './connectivity';
import * as path from 'path';
import express from "express";
const utils = require('../common/utils');
const dynamic = import('./dynamic-module');
"""
    imports = analyzer.extract_imports("component.tsx", content=ts_code)
    assert "./connectivity" in imports
    assert "path" in imports
    assert "express" in imports
    assert "../common/utils" in imports
    assert "./dynamic-module" in imports


def test_extract_imports_rust_and_go():
    """SPEC §29.6 line 7739: "STEAL: OpenHuman's import extraction patterns for .ts/.py/.rs." """
    analyzer = CodeGraphAnalyzer()
    rs_code = """
use std::collections::HashMap;
use crate::engine::router;
mod parser;
"""
    rs_imports = analyzer.extract_imports("lib.rs", content=rs_code)
    assert "std" in rs_imports
    assert "crate" in rs_imports
    assert "parser" in rs_imports

    go_code = """
package main
import "fmt"
import (
    "net/http"
    "github.com/gin-gonic/gin"
)
"""
    go_imports = analyzer.extract_imports("main.go", content=go_code)
    assert "fmt" in go_imports
    assert "net/http" in go_imports
    assert "github.com/gin-gonic/gin" in go_imports


def test_resolve_import_path_relative_and_module():
    """SPEC §29.6 line 7698: "resolved = resolve_import_path(imported_module, file.dir)" """
    analyzer = CodeGraphAnalyzer()
    all_files = {
        "src/index.ts",
        "src/connectivity.ts",
        "src/utils/math.ts",
        "sidecar/service.py",
        "sidecar/config.py",
    }

    # Relative resolution
    r1 = analyzer.resolve_import_path("./connectivity", "src", all_files)
    assert r1 == "src/connectivity.ts"

    # Upwards relative resolution
    r2 = analyzer.resolve_import_path("../connectivity", "src/utils", all_files)
    assert r2 == "src/connectivity.ts"

    # Python module dot resolution
    r3 = analyzer.resolve_import_path("sidecar.config", "sidecar", all_files)
    assert r3 == "sidecar/config.py"

    # Non-existent external module returns None
    r4 = analyzer.resolve_import_path("external_library", "src", all_files)
    assert r4 is None


def test_build_dependency_graph_and_roots(tmp_path: Path):
    """SPEC §29.6 line 7709: "entry_points: graph.find_roots() // files with no inbound imports" """
    (tmp_path / "a.py").write_text("import b", encoding="utf-8")
    (tmp_path / "b.py").write_text("import c", encoding="utf-8")
    (tmp_path / "c.py").write_text("# leaf", encoding="utf-8")
    (tmp_path / "isolated.py").write_text("# lone", encoding="utf-8")

    analyzer = CodeGraphAnalyzer()
    g = analyzer.build_dependency_graph(tmp_path)

    assert set(g.nodes) == {"a.py", "b.py", "c.py", "isolated.py"}
    # a.py -> b.py, b.py -> c.py
    edges_pairs = [(e["source"], e["target"]) for e in g.edges]
    assert ("a.py", "b.py") in edges_pairs
    assert ("b.py", "c.py") in edges_pairs

    # Roots: a.py and isolated.py have no inbound imports
    assert "a.py" in g.entry_points
    assert "isolated.py" in g.entry_points
    assert "b.py" not in g.entry_points
    assert "c.py" not in g.entry_points


def test_find_connected_components():
    """SPEC §29.6 line 7703: "Identify module clusters (strongly connected components)" """
    analyzer = CodeGraphAnalyzer()
    files = ["a.py", "b.py", "c.py", "d.py"]
    # Cycle between a and b: a -> b, b -> a
    # Chain: b -> c, d is isolated
    edges = [
        {"source": "a.py", "target": "b.py"},
        {"source": "b.py", "target": "a.py"},
        {"source": "b.py", "target": "c.py"},
    ]
    clusters = analyzer.find_connected_components(files, edges)
    # Strongly connected cluster with [a.py, b.py]
    scc_sizes = [len(c) for c in clusters]
    assert 2 in scc_sizes
    cyclic_cluster = next(c for c in clusters if len(c) == 2)
    assert set(cyclic_cluster) == {"a.py", "b.py"}


def test_calculate_centrality():
    """SPEC §29.6 line 7706: "Calculate file importance (PageRank-like)" """
    analyzer = CodeGraphAnalyzer()
    files = ["hub.py", "worker1.py", "worker2.py", "worker3.py"]
    # All workers import hub.py -> hub.py should have highest centrality
    edges = [
        {"source": "worker1.py", "target": "hub.py"},
        {"source": "worker2.py", "target": "hub.py"},
        {"source": "worker3.py", "target": "hub.py"},
    ]
    centrality = analyzer.calculate_centrality(files, edges)
    assert len(centrality) == 4
    assert centrality["hub.py"] > centrality["worker1.py"]
    assert centrality["hub.py"] > centrality["worker2.py"]
    assert centrality["hub.py"] > centrality["worker3.py"]
    # Sum of ranks approximately 1.0
    assert abs(sum(centrality.values()) - 1.0) < 0.01


def test_scope_task_files_with_transitive_dependents():
    """SPEC §29.6 line 7717: "Given a task description, identify the minimal set of files that need editing, expanded with transitive dependents (depth=2)" """
    analyzer = CodeGraphAnalyzer()
    graph = {
        "files": ["sidecar/connectivity.py", "sidecar/service.py", "extension/client.ts", "unrelated/auth.py"],
        "edges": [
            # service imports connectivity
            {"source": "sidecar/service.py", "target": "sidecar/connectivity.py"},
            # client imports service
            {"source": "extension/client.ts", "target": "sidecar/service.py"},
        ],
    }
    # Task touches connectivity
    scoped = analyzer.scope_task_files("Fix connectivity probe timeout handling", graph, depth=2)
    assert "sidecar/connectivity.py" in scoped["seed_files"]
    # Transitive dependents: service (depth 1) and client (depth 2)
    assert "sidecar/service.py" in scoped["expanded_files"]
    assert "extension/client.ts" in scoped["expanded_files"]
    assert "unrelated/auth.py" not in scoped["expanded_files"]


def test_graphify_integration_and_staleness(tmp_path: Path):
    """SPEC §29.6 line 7725: "If graphify-out/graph.json exists and is fresh (<24h), use it directly instead of running the lightweight scanner" """
    graphify_dir = tmp_path / "graphify-out"
    graphify_dir.mkdir()
    graph_json = graphify_dir / "graph.json"

    graph_data = {
        "nodes": [{"id": "pkg/mod1.py"}, {"id": "pkg/mod2.py"}],
        "links": [{"source": "pkg/mod1.py", "target": "pkg/mod2.py", "type": "imports"}],
    }
    graph_json.write_text(json.dumps(graph_data), encoding="utf-8")

    analyzer = CodeGraphAnalyzer()
    # 1. Fresh graph loads graphify directly
    g_fresh = analyzer.get_or_build_graph(tmp_path, max_age_hours=24.0)
    assert g_fresh.source == "graphify"
    assert "pkg/mod1.py" in g_fresh.nodes
    assert "pkg/mod2.py" in g_fresh.nodes

    # 2. Stale graph falls back to scanner
    g_stale = analyzer.get_or_build_graph(tmp_path, max_age_hours=0.0)  # max age 0 means stale
    assert g_stale.source == "ast_scanner"


def test_modular_off_switch_returns_503(monkeypatch):
    """SPEC §29.6 line 7738: "Swappable / off state: locus.code_graph.enabled. Off -> returns 503." """
    monkeypatch.setattr(config, "get", lambda k, default=None: False if "enabled" in k else default)

    prov = DefaultCodeGraphProvider()
    ok, reason = prov.is_feature_enabled()
    assert not ok
    assert "disabled" in reason.lower()

    # Off-switch causes methods to return status 503
    res_analyze = prov.analyze_codebase(".")
    assert res_analyze.get("status_code") == 503

    res_scope = prov.scope_task_files("test task", ".")
    assert res_scope.get("status_code") == 503

    res_graph = prov.get_or_build_graph(".")
    assert res_graph.get("status_code") == 503

    res_status = prov.get_status()
    assert res_status.get("status_code") == 503


def test_provider_swappability():
    """SPEC §29.6 line 7738: "Swappable / off state: BaseCodeGraphProvider interface allows custom provider implementations." """
    class CustomCodeGraphProvider(BaseCodeGraphProvider):
        @property
        def name(self) -> str:
            return "mock_custom_provider"

        def is_feature_enabled(self) -> Tuple[bool, str]:
            return True, "Enabled"

        def analyze_codebase(self, project_path: str) -> Dict[str, Any]:
            return {"provider": self.name, "files": ["custom.py"], "edges": []}

        def scope_task_files(self, task_description: str, project_path: str, depth: int = 2) -> Dict[str, Any]:
            return {"provider": self.name, "seed_files": ["custom.py"], "expanded_files": []}

        def get_or_build_graph(self, project_path: str, max_age_hours: float = 24.0) -> Dict[str, Any]:
            return {"provider": self.name, "files": ["custom.py"]}

        def get_status(self) -> Dict[str, Any]:
            return {"provider": self.name, "online": True}

    custom: BaseCodeGraphProvider = CustomCodeGraphProvider()
    assert custom.name == "mock_custom_provider"
    assert custom.analyze_codebase(".")["files"] == ["custom.py"]
