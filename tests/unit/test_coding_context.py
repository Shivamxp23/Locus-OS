"""
Unit tests for Coding Context Engine (SPEC §6.3 / F-0029).
"""
from __future__ import annotations

from pathlib import Path
import pytest

from sidecar.context.coding_context import (
    ASTRepoMapGenerator,
    ASTTag,
    CodingContextEngine,
    GitMetadataCollector,
    WorkspaceCodingState,
)
from sidecar.providers.coding_context import (
    BaseCodingContextProvider,
    DefaultCodingContextProvider,
)
import sidecar.config as config


def test_workspace_coding_state_data_structure() -> None:
    """SPEC §6.3 line 2137: "DATA STRUCTURES: WorkspaceCodingState: repo_root: string, active_branch: string..." """
    state = WorkspaceCodingState(
        repo_root="/repo",
        active_branch="feature-x",
        dirty_files=["src/main.py"],
        staged_diff_stat="1 file changed",
        unstaged_diff_stat="2 files changed",
        repo_map_snippet="src/main.py:\n  def run()",
        recent_edits=["src/main.py"],
    )
    d = state.to_dict()
    assert d["repo_root"] == "/repo"
    assert d["active_branch"] == "feature-x"
    assert d["dirty_files"] == ["src/main.py"]

    recovered = WorkspaceCodingState.from_dict(d)
    assert recovered.active_branch == "feature-x"
    assert recovered.repo_map_snippet == "src/main.py:\n  def run()"


def test_git_metadata_collector(tmp_path: Path) -> None:
    """SPEC §6.3 line 2149: "state.active_branch = git_current_branch(repo_path)" """
    collector = GitMetadataCollector(tmp_path)
    branch = collector.get_branch()
    assert isinstance(branch, str)

    dirty = collector.get_dirty_files()
    assert isinstance(dirty, list)

    stat = collector.get_diff_stat()
    assert isinstance(stat, str)


def test_ast_tag_extraction_and_pagerank(tmp_path: Path) -> None:
    """SPEC §6.3 line 2154: "tags = extract_ast_tags(repo_path) // Tree-sitter extraction of classes, functions, interfaces" """
    py1 = tmp_path / "engine.py"
    py1.write_text(
        "class Engine:\n"
        "    def start(self): pass\n"
        "    def stop(self): pass\n"
        "def helper(): pass\n",
        encoding="utf-8",
    )
    py2 = tmp_path / "consumer.py"
    py2.write_text(
        "from engine import Engine\n"
        "def run_consumer():\n"
        "    e = Engine()\n"
        "    e.start()\n",
        encoding="utf-8",
    )

    generator = ASTRepoMapGenerator(tmp_path)
    tags1 = generator.extract_file_tags(py1)
    assert any(t.name == "Engine" and t.kind == "class" for t in tags1)
    assert any(t.name == "start" and t.kind == "method" for t in tags1)
    assert any(t.name == "helper" and t.kind == "function" for t in tags1)

    tags2 = generator.extract_file_tags(py2)
    assert any(t.name == "run_consumer" for t in tags2)

    file_tags = {"engine.py": tags1, "consumer.py": tags2}
    ranked = generator.compute_pagerank(file_tags)
    assert len(ranked) == 2
    # engine.py is referenced by consumer.py, so it has higher/equal centrality
    assert ranked[0] == "engine.py"


def test_repo_map_budget_enforcement(tmp_path: Path) -> None:
    """SPEC §6.3 line 2162: "IF current_tokens + tree_tokens > token_budget: BREAK" """
    for i in range(15):
        f = tmp_path / f"module_{i}.py"
        f.write_text(f"class Class{i}:\n    def method_{i}(self): pass\ndef func_{i}(): pass\n", encoding="utf-8")

    generator = ASTRepoMapGenerator(tmp_path)
    # Strict 20-token budget should cap included files
    repo_map_small = generator.generate_repo_map(token_budget=20)
    assert len(repo_map_small.splitlines()) < 15

    # Generous budget includes more files
    repo_map_large = generator.generate_repo_map(token_budget=1000)
    assert len(repo_map_large.splitlines()) > len(repo_map_small.splitlines())


def test_generate_coding_context_layer(tmp_path: Path) -> None:
    """SPEC §6.3 line 2174: "FUNCTION format_coding_context_layer(state: WorkspaceCodingState) -> string:" """
    py_file = tmp_path / "server.py"
    py_file.write_text("class Server:\n    def serve(self): pass\n", encoding="utf-8")

    engine = CodingContextEngine(repo_root=tmp_path)
    state = engine.generate_coding_context(token_budget=300)

    assert state.repo_root == str(tmp_path)
    assert "Server" in state.repo_map_snippet

    formatted = engine.format_coding_context_layer(state)
    assert "[CODING CONTEXT]" in formatted
    assert f"Branch: {state.active_branch}" in formatted
    assert "Repo Map:" in formatted
    assert "server.py:" in formatted


def test_coding_context_provider_off_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §6.3 line 2187: "Swappable / off state: locus.context.coding_map.enabled. Off -> coding context omitted from prompt; agent relies on explicit tool lookups." """
    provider = DefaultCodingContextProvider(repo_root=tmp_path)
    assert provider.is_available() is True

    # Disable via config
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "coding" in key else default)
    assert provider.is_available() is False

    state = provider.get_coding_context(token_budget=500)
    # When off, repo_map_snippet is empty and format_layer returns empty string
    assert state.repo_map_snippet == ""
    assert provider.format_layer(state) == ""
