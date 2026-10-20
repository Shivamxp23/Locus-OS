"""
Unit tests for Dynamic Context References (SPEC §6.2 / F-0028).
"""
from __future__ import annotations

from pathlib import Path
import pytest

from sidecar.context.references import (
    ContextRefType,
    ContextReferenceResolver,
    ResolvedReference,
    count_tokens,
    parse_path_and_lines,
    truncate_to_tokens,
)
from sidecar.providers.context_references import (
    BaseContextReferenceProvider,
    DefaultContextReferenceProvider,
)
import sidecar.config as config


def test_context_ref_types_and_parser_regex() -> None:
    """SPEC §6.2 line 2043: "ContextRefType: FILE = '@file' // @file:src/main.ts#L10-L45" """
    assert ContextRefType.FILE.value == "@file"
    assert ContextRefType.DIR.value == "@dir"
    assert ContextRefType.SYMBOL.value == "@symbol"
    assert ContextRefType.GIT.value == "@git"
    assert ContextRefType.DIFF.value == "@diff"
    assert ContextRefType.URL.value == "@url"

    path, start, end = parse_path_and_lines("src/main.ts#L10-L45")
    assert path == "src/main.ts"
    assert start == 10
    assert end == 45

    path2, start2, end2 = parse_path_and_lines("app.py#L20")
    assert path2 == "app.py"
    assert start2 == 20
    assert end2 == 20

    path3, start3, end3 = parse_path_and_lines("plain_file.txt")
    assert path3 == "plain_file.txt"
    assert start3 is None
    assert end3 is None


def test_file_reference_resolution(tmp_path: Path) -> None:
    """SPEC §6.2 line 2070: "path, start_line, end_line = parse_path_and_lines(target)" """
    test_file = tmp_path / "sample.py"
    lines = [f"line_{i} = {i}" for i in range(1, 31)]
    test_file.write_text("\n".join(lines), encoding="utf-8")

    resolver = ContextReferenceResolver(repo_root=tmp_path)
    prompt = "Please inspect @file:sample.py#L5-L10 in detail."
    clean_prompt, refs = resolver.extract_and_resolve_references(prompt)

    assert "[FILE: sample.py#L5-L10]" in clean_prompt
    assert len(refs) == 1
    ref = refs[0]
    assert ref.ref_type == ContextRefType.FILE
    assert "line_5 = 5" in ref.content
    assert "line_10 = 10" in ref.content
    assert "line_11 = 11" not in ref.content


def test_symbol_reference_resolution(tmp_path: Path) -> None:
    """SPEC §6.2 line 2090: "ELIF ref_kind == 'symbol': content = ast_lookup_symbol(target)" """
    code_file = tmp_path / "module.py"
    code_file.write_text(
        "def compute_trajectory(alpha: float, beta: float) -> float:\n"
        "    '''Compute orbital trajectory.'''\n"
        "    return alpha * 2.0 + beta\n\n"
        "class OrbitalEngine:\n"
        "    pass\n",
        encoding="utf-8",
    )

    resolver = ContextReferenceResolver(repo_root=tmp_path)
    prompt = "Check function @symbol:compute_trajectory for stability."
    clean_prompt, refs = resolver.extract_and_resolve_references(prompt)

    assert "[SYMBOL: compute_trajectory]" in clean_prompt
    assert len(refs) == 1
    ref = refs[0]
    assert ref.ref_type == ContextRefType.SYMBOL
    assert "def compute_trajectory" in ref.content
    assert "Compute orbital trajectory" in ref.content


def test_git_reference_resolution(tmp_path: Path) -> None:
    """SPEC §6.2 line 2085: "ELIF ref_kind == 'git': IF target == 'status': content = git_status()" """
    resolver = ContextReferenceResolver(repo_root=tmp_path)
    prompt = "Show current @git:status and changes."
    clean_prompt, refs = resolver.extract_and_resolve_references(prompt)

    assert "[GIT: status]" in clean_prompt
    assert len(refs) == 1
    assert refs[0].ref_type == ContextRefType.GIT


def test_token_budget_truncation(tmp_path: Path) -> None:
    """SPEC §6.2 line 2073: "IF tokens > remaining_budget: content = truncate_to_tokens(content, remaining_budget); truncated = True" """
    large_file = tmp_path / "large.txt"
    large_file.write_text("A" * 8000, encoding="utf-8")

    resolver = ContextReferenceResolver(repo_root=tmp_path)
    prompt = "Examine @file:large.txt please."
    clean_prompt, refs = resolver.extract_and_resolve_references(prompt, max_ref_budget=100)

    assert len(refs) == 1
    assert refs[0].truncated is True
    assert "TRUNCATED" in refs[0].content


def test_format_references_xml() -> None:
    """SPEC §6.2 line 2104: "FUNCTION format_references_xml(refs: List[ResolvedReference]) -> string:" """
    refs = [
        ResolvedReference(ContextRefType.FILE, "src/core.py", "def run(): pass", 10),
        ResolvedReference(ContextRefType.GIT, "status", "M sidecar/service.py", 8),
    ]
    resolver = ContextReferenceResolver()
    xml = resolver.format_references_xml(refs)

    assert '<context_ref type="@file" target="src/core.py">' in xml
    assert "def run(): pass" in xml
    assert '<context_ref type="@git" target="status">' in xml
    assert "</context_ref>" in xml


def test_context_references_provider_off_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §6.2 line 2115: "Swappable / off state: locus.context.references.enabled. Off -> @ tags are treated as literal text; no file resolution occurs." """
    provider = DefaultContextReferenceProvider(repo_root=tmp_path)
    assert provider.is_available() is True

    # Disable via config
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "context_ref" in key or "context.ref" in key else default)
    assert provider.is_available() is False

    test_prompt = "Examine @file:some_file.py"
    clean_prompt, refs = provider.resolve_references(test_prompt)
    # Off state: tags treated as literal text, no references resolved
    assert clean_prompt == test_prompt
    assert refs == []
    assert provider.format_xml(refs) == ""
