"""
SPEC §6.3: Coding Context Engine (Repo Map, AST Index, Active Diff) (F-0029).
Extracts active workspace coding context (git branch, diff stat, dirty files)
and generates a concise PageRank-ranked repository AST skeleton within a token budget.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar.context.references import count_tokens


@dataclass
class WorkspaceCodingState:
    """SPEC §6.3 lines 2137-2144: WorkspaceCodingState data structure."""
    repo_root: str
    active_branch: str = "main"
    dirty_files: List[str] = field(default_factory=list)
    staged_diff_stat: str = ""
    unstaged_diff_stat: str = ""
    repo_map_snippet: str = ""
    recent_edits: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkspaceCodingState:
        return cls(
            repo_root=data.get("repo_root", ""),
            active_branch=data.get("active_branch", "main"),
            dirty_files=data.get("dirty_files") or [],
            staged_diff_stat=data.get("staged_diff_stat", ""),
            unstaged_diff_stat=data.get("unstaged_diff_stat", ""),
            repo_map_snippet=data.get("repo_map_snippet", ""),
            recent_edits=data.get("recent_edits") or [],
        )


@dataclass
class ASTTag:
    """Represents a code symbol extracted from an AST."""
    file_path: str
    name: str
    kind: str  # class | function | method | interface
    lineno: int
    parent: Optional[str] = None


class GitMetadataCollector:
    """Collects git metadata, branch names, dirty files, and diff stats."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def _run_git(self, args: List[str]) -> str:
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.stdout.strip()
        except Exception:
            return ""

    def get_branch(self) -> str:
        out = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return out or "unknown"

    def get_dirty_files(self) -> List[str]:
        out = self._run_git(["status", "--porcelain"])
        files: List[str] = []
        for line in out.splitlines():
            line = line.strip()
            if len(line) > 3:
                files.append(line[3:].strip())
        return files

    def get_diff_stat(self, staged: bool = False) -> str:
        args = ["diff", "--stat"]
        if staged:
            args.append("--cached")
        out = self._run_git(args)
        return out or "(clean)"

    def get_recent_edits(self, limit: int = 5) -> List[str]:
        out = self._run_git(["log", f"-n{limit}", "--name-only", "--pretty=format:"])
        edits: Set[str] = set()
        for line in out.splitlines():
            line = line.strip()
            if line:
                edits.add(line)
        return sorted(list(edits))[:limit]


class ASTRepoMapGenerator:
    """
    SPEC §6.3 lines 2154-2169:
    Tree-sitter/AST extraction of classes, functions, interfaces.
    PageRank / in-degree ranking across files to produce a concise skeleton within budget.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def extract_file_tags(self, file_path: Path) -> List[ASTTag]:
        """Extract classes and functions from a Python or TS/JS file."""
        rel_path = str(file_path.relative_to(self.repo_root)).replace("\\", "/")
        tags: List[ASTTag] = []

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8", errors="replace"))
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        tags.append(ASTTag(rel_path, node.name, "class", node.lineno))
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                tags.append(ASTTag(rel_path, item.name, "method", item.lineno, parent=node.name))
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        tags.append(ASTTag(rel_path, node.name, "function", node.lineno))
            except Exception:
                pass
        elif file_path.suffix in (".ts", ".js"):
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                for m in re.finditer(r"(?:export\s+)?(?:class|interface|type)\s+([A-Za-z0-9_]+)", text):
                    tags.append(ASTTag(rel_path, m.group(1), "class", 1))
                for m in re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)", text):
                    tags.append(ASTTag(rel_path, m.group(1), "function", 1))
            except Exception:
                pass

        return tags

    def compute_pagerank(self, file_tags: Dict[str, List[ASTTag]]) -> List[str]:
        """
        Compute simplified PageRank / connectivity ranking based on cross-file symbol references.
        """
        files = list(file_tags.keys())
        if not files:
            return []

        # Build symbol table: symbol_name -> defining_file
        symbol_to_file: Dict[str, str] = {}
        for f, tags in file_tags.items():
            for t in tags:
                symbol_to_file[t.name] = f

        # Adjacency matrix: references between files
        in_degrees: Dict[str, int] = {f: 1 for f in files}
        for f in files:
            full_path = self.repo_root / f
            if not full_path.is_file():
                continue
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                for sym, def_file in symbol_to_file.items():
                    if def_file != f and sym in content:
                        in_degrees[def_file] = in_degrees.get(def_file, 1) + 1
            except Exception:
                continue

        # Sort files descending by centrality / in-degree score
        ranked = sorted(files, key=lambda x: in_degrees.get(x, 1), reverse=True)
        return ranked

    def format_file_ast_skeleton(self, rel_path: str, tags: List[ASTTag]) -> str:
        """Format concise structural skeleton of a file."""
        lines = [f"{rel_path}:"]
        classes = [t for t in tags if t.kind == "class"]
        functions = [t for t in tags if t.kind == "function"]
        methods = [t for t in tags if t.kind == "method"]

        for c in classes:
            c_methods = [m.name for m in methods if m.parent == c.name]
            meth_str = f"({', '.join(c_methods[:4])})" if c_methods else ""
            lines.append(f"  class {c.name} {meth_str}")
        for fn in functions:
            lines.append(f"  def {fn.name}()")
        return "\n".join(lines)

    def generate_repo_map(self, token_budget: int = 500) -> str:
        """
        SPEC §6.3 lines 2154-2169:
        Assemble concise tree within budget.
        """
        candidate_files: List[Path] = []
        for ext in ("*.py", "*.ts"):
            for p in self.repo_root.rglob(ext):
                if any(part in p.parts for part in (".git", "node_modules", "dist", ".pytest_cache", "venv")):
                    continue
                candidate_files.append(p)
                if len(candidate_files) >= 50:
                    break

        file_tags: Dict[str, List[ASTTag]] = {}
        for p in candidate_files:
            rel = str(p.relative_to(self.repo_root)).replace("\\", "/")
            tags = self.extract_file_tags(p)
            if tags:
                file_tags[rel] = tags

        ranked_files = self.compute_pagerank(file_tags)

        repo_map: List[str] = []
        current_tokens = 0
        for f in ranked_files:
            skeleton = self.format_file_ast_skeleton(f, file_tags[f])
            tokens = count_tokens(skeleton)
            if current_tokens + tokens > token_budget:
                break
            repo_map.append(skeleton)
            current_tokens += tokens

        return "\n".join(repo_map)


class CodingContextEngine:
    """
    SPEC §6.3 lines 2146-2182:
    FUNCTION generate_coding_context(repo_path: string, token_budget: int = 500) -> WorkspaceCodingState
    FUNCTION format_coding_context_layer(state: WorkspaceCodingState) -> string
    """

    def __init__(self, repo_root: Optional[Path | str] = None) -> None:
        self.repo_root = Path(repo_root or Path.cwd())
        self.git_collector = GitMetadataCollector(self.repo_root)
        self.map_generator = ASTRepoMapGenerator(self.repo_root)

    def generate_coding_context(
        self,
        token_budget: int = 500,
    ) -> WorkspaceCodingState:
        """SPEC §6.3 lines 2146-2172: Generate full workspace coding state."""
        state = WorkspaceCodingState(repo_root=str(self.repo_root))
        # 1. Gather Git Metadata
        state.active_branch = self.git_collector.get_branch()
        state.dirty_files = self.git_collector.get_dirty_files()
        state.staged_diff_stat = self.git_collector.get_diff_stat(staged=True)
        state.unstaged_diff_stat = self.git_collector.get_diff_stat(staged=False)
        state.recent_edits = self.git_collector.get_recent_edits()

        # 2. Generate PageRank Repo Map
        state.repo_map_snippet = self.map_generator.generate_repo_map(token_budget=token_budget)
        return state

    def format_coding_context_layer(self, state: WorkspaceCodingState) -> str:
        """
        SPEC §6.3 lines 2174-2182:
        FUNCTION format_coding_context_layer(state: WorkspaceCodingState) -> string:
            RETURN f'''[CODING CONTEXT]
        Branch: {state.active_branch} | Dirty files: {len(state.dirty_files)}
        Diff Stat: {state.unstaged_diff_stat}
        Repo Map:
        {state.repo_map_snippet}'''
        """
        return (
            f"[CODING CONTEXT]\n"
            f"Branch: {state.active_branch} | Dirty files: {len(state.dirty_files)}\n"
            f"Diff Stat: {state.unstaged_diff_stat}\n"
            f"Repo Map:\n"
            f"{state.repo_map_snippet}"
        )
