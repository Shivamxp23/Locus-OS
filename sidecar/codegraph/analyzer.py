"""
Code Graph Analysis engine (SPEC §29.6 / F-0069 / US-107).

Implements codebase scanning, multi-language import extraction,
dependency graph creation, strongly connected components (clustering),
PageRank centrality, task file scoping with transitive dependents,
and /graphify integration fallback.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger("locus.codegraph.analyzer")

SUPPORTED_EXTENSIONS: Set[str] = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".py",
    ".rs",
    ".go",
}

DEFAULT_EXCLUDES: Set[str] = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".locus",
    ".cache",
    ".pytest_cache",
    "venv",
    ".venv",
    "env",
    "target",
}


@dataclass
class DependencyGraph:
    """Directed dependency graph of files and import relationships."""
    nodes: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    clusters: List[List[str]] = field(default_factory=list)
    importance: Dict[str, float] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    source: str = "ast_scanner"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files": self.nodes,
            "edges": self.edges,
            "clusters": self.clusters,
            "importance": self.importance,
            "entry_points": self.entry_points,
            "source": self.source,
        }


class CodeGraphAnalyzer:
    """
    Codebase dependency graph builder and task file scoping engine.
    Follows SPEC §29.6 logic decomposition.
    """

    def __init__(
        self,
        extensions: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> None:
        self.extensions = set(extensions) if extensions else set(SUPPORTED_EXTENSIONS)
        self.exclude = set(exclude) if exclude else set(DEFAULT_EXCLUDES)

    def scan_directory(
        self,
        project_path: str | Path,
        extensions: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
    ) -> List[str]:
        """
        Scan project directory for source files matching extensions,
        excluding designated directory trees.
        Returns sorted relative POSIX paths.
        """
        root = Path(project_path).resolve()
        if not root.is_dir():
            return []

        exts = set(extensions) if extensions else self.extensions
        excls = set(exclude) if exclude else self.exclude

        results: List[str] = []

        for p in root.rglob("*"):
            if not p.is_file():
                continue

            rel_parts = p.relative_to(root).parts
            # Skip if any segment is in exclusions
            if any(part in excls for part in rel_parts):
                continue

            if p.suffix.lower() in exts:
                posix_rel = p.relative_to(root).as_posix()
                results.append(posix_rel)

        results.sort()
        return results

    def extract_imports(
        self,
        file_path: str | Path,
        content: Optional[str] = None,
    ) -> List[str]:
        """
        Extract imported modules or file paths from file content based on extension.
        Supports Python (.py), TypeScript/JavaScript (.ts/.tsx/.js/.jsx),
        Rust (.rs), and Go (.go).
        """
        p = Path(file_path)
        ext = p.suffix.lower()

        if content is None:
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                return []

        imports: List[str] = []

        if ext == ".py":
            # Python: import foo, from foo.bar import baz, from .foo import bar
            for m in re.finditer(r"^[ \t]*(?:from[ \t]+([a-zA-Z0-9_\.]+)[ \t]+import|import[ \t]+([a-zA-Z0-9_,\. \t]+))", content, re.M):
                mod_from, mod_import = m.group(1), m.group(2)
                if mod_from:
                    imports.append(mod_from.strip())
                elif mod_import:
                    for sub in mod_import.split(","):
                        cand = sub.strip().split()[0] if sub.strip() else ""
                        if cand:
                            imports.append(cand)

        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            # TS/JS: import ... from '...'; import('...'); require('...')
            for m in re.finditer(r"""(?:import\s+[\w\s{},*]*\s+from\s+['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)|require\s*\(\s*['"]([^'"]+)['"]\s*\))""", content):
                cand = m.group(1) or m.group(2) or m.group(3)
                if cand:
                    imports.append(cand.strip())

        elif ext == ".rs":
            # Rust: use foo::bar; mod foo;
            for m in re.finditer(r"^\s*use\s+([a-zA-Z0-9_:]+)", content, re.M):
                cand = m.group(1).split("::")[0].strip()
                if cand:
                    imports.append(cand)
            for m in re.finditer(r"^\s*mod\s+([a-zA-Z0-9_]+);", content, re.M):
                cand = m.group(1).strip()
                if cand:
                    imports.append(cand)

        elif ext == ".go":
            # Go: import "foo/bar" or import ( "foo" )
            single_matches = re.finditer(r'import\s+"([^"]+)"', content)
            for m in single_matches:
                imports.append(m.group(1).strip())
            multi_block = re.search(r'import\s*\(([^)]+)\)', content, re.S)
            if multi_block:
                for ln in multi_block.group(1).splitlines():
                    sub = re.search(r'"([^"]+)"', ln)
                    if sub:
                        imports.append(sub.group(1).strip())

        return sorted(list(set(imports)))

    def resolve_import_path(
        self,
        imported_module: str,
        file_dir: str,
        all_files: Set[str],
    ) -> Optional[str]:
        """
        Resolve an imported module string to a known project file in all_files.
        Handles relative imports (./foo, ../bar) and top-level / module imports.
        """
        imported_module = imported_module.strip()
        if not imported_module:
            return None

        # Candidate suffixes to test
        suffixes = ["", ".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", "/index.ts", "/index.js"]

        # 1. Relative import (starts with . or ..)
        if imported_module.startswith("."):
            base = Path(file_dir) / imported_module
            normalized = base.as_posix()
            # Collapse dots
            clean_parts = []
            for part in normalized.split("/"):
                if part == "." or part == "":
                    continue
                elif part == "..":
                    if clean_parts:
                        clean_parts.pop()
                else:
                    clean_parts.append(part)
            clean_str = "/".join(clean_parts)

            for sfx in suffixes:
                cand = clean_str + sfx
                if cand in all_files:
                    return cand
            return None

        # 2. Python module dot notation (e.g., sidecar.diagnostics.connectivity)
        dot_as_path = imported_module.replace(".", "/")
        for sfx in suffixes:
            cand = dot_as_path + sfx
            if cand in all_files:
                return cand

        # 3. Direct match
        for sfx in suffixes:
            cand = imported_module + sfx
            if cand in all_files:
                return cand

        return None

    def find_connected_components(
        self,
        files: List[str],
        edges: List[Dict[str, Any]],
    ) -> List[List[str]]:
        """
        Find strongly connected components (SCCs / clusters) in the directed graph
        using Tarjan's algorithm. Single nodes and cyclic clusters are partitioned.
        """
        adj: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            adj[e["source"]].append(e["target"])

        index = 0
        indices: Dict[str, int] = {}
        lowlinks: Dict[str, int] = {}
        on_stack: Set[str] = set()
        stack: List[str] = []
        components: List[List[str]] = []

        def strongconnect(v: str) -> None:
            nonlocal index
            indices[v] = index
            lowlinks[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)

            for w in adj.get(v, []):
                if w not in indices:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])

            if lowlinks[v] == indices[v]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == v:
                        break
                components.append(sorted(scc))

        for f in files:
            if f not in indices:
                strongconnect(f)

        components.sort(key=lambda c: (-len(c), c[0] if c else ""))
        return components

    def calculate_centrality(
        self,
        files: List[str],
        edges: List[Dict[str, Any]],
        damping: float = 0.85,
        iterations: int = 25,
    ) -> Dict[str, float]:
        """
        Calculate PageRank-like centrality scores for all files.
        Files that are imported by many other files receive higher centrality.
        """
        if not files:
            return {}

        n = len(files)
        # Note: in dependency graphs, file A imports B means A -> B.
        # B is "important" because it is a dependency of A.
        # Therefore, inbound edges to B represent inbound references.
        in_edges: Dict[str, List[str]] = defaultdict(list)
        out_degree: Dict[str, int] = defaultdict(int)

        for e in edges:
            src, tgt = e["source"], e["target"]
            if src in files and tgt in files:
                in_edges[tgt].append(src)
                out_degree[src] += 1

        rank = {f: 1.0 / n for f in files}

        for _ in range(iterations):
            new_rank: Dict[str, float] = {}
            dangling_sum = sum(rank[f] for f in files if out_degree[f] == 0)

            for f in files:
                incoming_sum = sum(
                    rank[src] / out_degree[src]
                    for src in in_edges.get(f, [])
                    if out_degree[src] > 0
                )
                score = (1.0 - damping) / n + damping * (incoming_sum + dangling_sum / n)
                new_rank[f] = score

            rank = new_rank

        # Normalize to sum to 1.0
        total = sum(rank.values()) or 1.0
        return {k: round(v / total, 6) for k, v in rank.items()}

    def find_roots(
        self,
        files: List[str],
        edges: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Identify entry points / roots (files with no inbound imports from project files).
        """
        has_inbound: Set[str] = {e["target"] for e in edges}
        roots = [f for f in files if f not in has_inbound]
        roots.sort()
        return roots

    def build_dependency_graph(
        self,
        project_path: str | Path,
    ) -> DependencyGraph:
        """
        Full dependency graph construction for project directory.
        Scans files, extracts and resolves imports, discovers clusters,
        computes centrality and root entry points.
        """
        root = Path(project_path).resolve()
        files = self.scan_directory(root)
        files_set = set(files)

        edges: List[Dict[str, Any]] = []

        for rel_file in files:
            full_path = root / rel_file
            dir_posix = Path(rel_file).parent.as_posix()
            raw_imports = self.extract_imports(full_path)

            for raw_imp in raw_imports:
                resolved = self.resolve_import_path(raw_imp, dir_posix, files_set)
                if resolved and resolved != rel_file:
                    edge = {
                        "source": rel_file,
                        "target": resolved,
                        "type": "imports",
                        "raw": raw_imp,
                    }
                    if edge not in edges:
                        edges.append(edge)

        clusters = self.find_connected_components(files, edges)
        importance = self.calculate_centrality(files, edges)
        roots = self.find_roots(files, edges)

        return DependencyGraph(
            nodes=files,
            edges=edges,
            clusters=clusters,
            importance=importance,
            entry_points=roots,
            source="ast_scanner",
        )

    def scope_task_files(
        self,
        task_description: str,
        graph: Dict[str, Any] | DependencyGraph,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Given a task description, identify the minimal set of files that need editing
        and expand with transitive dependents (files that import the changed files)
        up to `depth` levels. Used by harness delegation (§3.7) to scope coding tasks.
        """
        if isinstance(graph, DependencyGraph):
            g_dict = graph.to_dict()
        else:
            g_dict = graph

        files: List[str] = g_dict.get("files", [])
        edges: List[Dict[str, Any]] = g_dict.get("edges", [])

        # Tokenize task description into search keywords
        raw_tokens = re.findall(r"[a-zA-Z0-9_\-]+", task_description.lower())
        tokens = {t for t in raw_tokens if len(t) >= 3 and t not in {"the", "and", "for", "with", "this", "that"}}

        seed_files: List[str] = []
        for f in files:
            f_lower = f.lower()
            name_parts = re.findall(r"[a-zA-Z0-9_]+", f_lower)
            if any(tok in name_parts or tok in f_lower for tok in tokens):
                seed_files.append(f)

        # Invert edges: dependent imports target -> dependent needs updating if target changes
        # edge: source -> target means source imports target
        # If target changes, source is a dependent that must be re-tested/scoped
        dependents_map: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            dependents_map[e["target"]].append(e["source"])

        expanded: Set[str] = set(seed_files)
        current_layer = set(seed_files)

        for _ in range(depth):
            next_layer: Set[str] = set()
            for seed in current_layer:
                for dep in dependents_map.get(seed, []):
                    if dep not in expanded:
                        expanded.add(dep)
                        next_layer.add(dep)
            current_layer = next_layer
            if not current_layer:
                break

        return {
            "task_description": task_description,
            "seed_files": sorted(seed_files),
            "expanded_files": sorted(list(expanded)),
            "depth": depth,
            "total_scoped": len(expanded),
        }

    def load_graphify_graph(
        self,
        graphify_path: str | Path,
    ) -> DependencyGraph:
        """
        Load and adapt graph data produced by /graphify (graphify-out/graph.json).
        """
        p = Path(graphify_path)
        data = json.loads(p.read_text(encoding="utf-8"))

        # Graphify graph structure has nodes and links/edges
        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("links", []) or data.get("edges", [])

        files: List[str] = []
        for n in raw_nodes:
            nid = n.get("id") or n.get("name")
            if nid and isinstance(nid, str):
                files.append(nid.replace("\\", "/"))

        edges: List[Dict[str, Any]] = []
        for e in raw_edges:
            src = e.get("source")
            tgt = e.get("target")
            if isinstance(src, dict):
                src = src.get("id")
            if isinstance(tgt, dict):
                tgt = tgt.get("id")
            if src and tgt:
                edges.append({
                    "source": str(src).replace("\\", "/"),
                    "target": str(tgt).replace("\\", "/"),
                    "type": e.get("type", "imports"),
                })

        clusters = self.find_connected_components(files, edges)
        importance = self.calculate_centrality(files, edges)
        roots = self.find_roots(files, edges)

        return DependencyGraph(
            nodes=sorted(list(set(files))),
            edges=edges,
            clusters=clusters,
            importance=importance,
            entry_points=roots,
            source="graphify",
        )

    def get_or_build_graph(
        self,
        project_path: str | Path,
        max_age_hours: float = 24.0,
    ) -> DependencyGraph:
        """
        Integration with /graphify:
        If graphify-out/graph.json exists and is fresh (<24h), use it directly
        instead of running the lightweight AST scanner.
        """
        root = Path(project_path).resolve()
        graphify_file = root / "graphify-out" / "graph.json"

        if graphify_file.is_file():
            try:
                mtime = graphify_file.stat().st_mtime
                age_hours = (time.time() - mtime) / 3600.0
                if age_hours < max_age_hours:
                    logger.info(f"Using fresh graphify graph ({age_hours:.1f}h old): {graphify_file}")
                    return self.load_graphify_graph(graphify_file)
            except Exception as e:
                logger.warning(f"Error checking/reading graphify graph: {e}")

        # Fallback to local codebase analysis
        return self.build_dependency_graph(root)
