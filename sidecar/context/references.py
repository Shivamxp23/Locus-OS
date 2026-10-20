"""
SPEC §6.2: Dynamic Context References (@file, @symbol, @git, @diff) (F-0028).
Parses @ prefix reference tags in user prompts; resolves files, symbols,
git state, and URLs into bounded context chunks formatted as <context_ref> XML.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# SPEC §6.2 lines 2043-2050: ContextRefType enum
class ContextRefType(str, Enum):
    FILE = "@file"
    DIR = "@dir"
    SYMBOL = "@symbol"
    GIT = "@git"
    DIFF = "@diff"
    URL = "@url"


# SPEC §6.2 lines 2052-2057: ResolvedReference structure
@dataclass
class ResolvedReference:
    ref_type: ContextRefType
    target_path: str
    content: str
    token_count: int
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_type": self.ref_type.value,
            "target_path": self.target_path,
            "content": self.content,
            "token_count": self.token_count,
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResolvedReference:
        raw_type = data.get("ref_type", "@file")
        try:
            rt = ContextRefType(raw_type)
        except ValueError:
            rt = ContextRefType.FILE
        return cls(
            ref_type=rt,
            target_path=data.get("target_path", ""),
            content=data.get("content", ""),
            token_count=int(data.get("token_count", 0)),
            truncated=bool(data.get("truncated", False)),
        )


def count_tokens(text: str) -> int:
    """Approximate token count for budgeting (4 characters per token average)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximate token budget."""
    char_limit = max_tokens * 4
    if len(text) <= char_limit:
        return text
    return text[:char_limit] + "\n... [TRUNCATED DUE TO CONTEXT BUDGET]"


# SPEC §6.2 line 2060: REFERENCE PARSER REGEX
PATTERN = re.compile(r"(@(file|dir|symbol|git|diff|url):([^\s\n]+))")


def parse_path_and_lines(target: str) -> Tuple[str, Optional[int], Optional[int]]:
    """Parse '@file:path#L10-L45' into (path, start_line, end_line)."""
    if "#" in target:
        path, fragment = target.split("#", 1)
        line_match = re.match(r"L?(\d+)(?:-L?(\d+))?", fragment, re.IGNORECASE)
        if line_match:
            start = int(line_match.group(1))
            end = int(line_match.group(2)) if line_match.group(2) else start
            return path, start, end
        return path, None, None
    return target, None, None


class ContextReferenceResolver:
    """
    SPEC §6.2: Resolves dynamic @-references within user prompts into structured bounded context.
    """

    def __init__(self, repo_root: Optional[Path | str] = None) -> None:
        if repo_root is None:
            self.repo_root = Path.cwd()
        else:
            self.repo_root = Path(repo_root)

    def extract_and_resolve_references(
        self,
        user_prompt: str,
        max_ref_budget: int = 1500,
    ) -> Tuple[str, List[ResolvedReference]]:
        """
        SPEC §6.2 lines 2062-2101:
        FUNCTION extract_and_resolve_references(user_prompt: string, max_ref_budget: int = 1500) -> Tuple[string, List[ResolvedReference]]:
            matches = regex_findall(PATTERN, user_prompt)
            resolved_refs = []
            clean_prompt = user_prompt
            allocated_tokens = 0
            ...
        """
        matches = PATTERN.findall(user_prompt)
        resolved_refs: List[ResolvedReference] = []
        clean_prompt = user_prompt
        allocated_tokens = 0

        for full_tag, ref_kind, target in matches:
            if allocated_tokens >= max_ref_budget:
                break

            remaining_budget = max_ref_budget - allocated_tokens
            ref_kind_lower = ref_kind.lower()

            if ref_kind_lower == "file":
                ref = self._resolve_file(target, remaining_budget)
            elif ref_kind_lower == "dir":
                ref = self._resolve_dir(target, remaining_budget)
            elif ref_kind_lower == "symbol":
                ref = self._resolve_symbol(target, remaining_budget)
            elif ref_kind_lower == "git":
                ref = self._resolve_git(target, remaining_budget)
            elif ref_kind_lower == "diff":
                ref = self._resolve_diff(target, remaining_budget)
            elif ref_kind_lower == "url":
                ref = self._resolve_url(target, remaining_budget)
            else:
                continue

            resolved_refs.append(ref)
            tokens_used = ref.token_count
            allocated_tokens += min(tokens_used, remaining_budget)

            # Replace tag in user prompt with clean reference identifier
            clean_prompt = clean_prompt.replace(full_tag, f"[{ref_kind.upper()}: {target}]")

        return clean_prompt, resolved_refs

    def _resolve_file(self, target: str, remaining_budget: int) -> ResolvedReference:
        path_str, start_line, end_line = parse_path_and_lines(target)
        file_path = self.repo_root / path_str
        if not file_path.is_file():
            content = f"Error: File not found: {path_str}"
            tokens = count_tokens(content)
            return ResolvedReference(ContextRefType.FILE, target, content, tokens, False)

        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if start_line is not None and end_line is not None:
                s = max(0, start_line - 1)
                e = min(len(lines), end_line)
                selected = lines[s:e]
                numbered = [f"{s + idx + 1:4d} | {line}" for idx, line in enumerate(selected)]
                content = "\n".join(numbered)
            else:
                content = "\n".join(lines)
        except Exception as ex:
            content = f"Error reading {path_str}: {ex}"

        tokens = count_tokens(content)
        truncated = False
        if tokens > remaining_budget:
            content = truncate_to_tokens(content, remaining_budget)
            tokens = count_tokens(content)
            truncated = True

        return ResolvedReference(ContextRefType.FILE, target, content, tokens, truncated)

    def _resolve_dir(self, target: str, remaining_budget: int) -> ResolvedReference:
        dir_path = self.repo_root / target
        if not dir_path.is_dir():
            content = f"Error: Directory not found: {target}"
            tokens = count_tokens(content)
            return ResolvedReference(ContextRefType.DIR, target, content, tokens, False)

        entries: list[str] = []
        for p in sorted(dir_path.iterdir()):
            if p.name.startswith("."):
                continue
            suffix = "/" if p.is_dir() else ""
            entries.append(f"{p.name}{suffix}")

        content = f"Directory contents for {target}:\n" + "\n".join(f"- {e}" for e in entries[:50])
        tokens = count_tokens(content)
        truncated = False
        if tokens > remaining_budget:
            content = truncate_to_tokens(content, remaining_budget)
            tokens = count_tokens(content)
            truncated = True
        return ResolvedReference(ContextRefType.DIR, target, content, tokens, truncated)

    def _resolve_symbol(self, target: str, remaining_budget: int) -> ResolvedReference:
        """Find a symbol definition across repository Python files via AST parsing."""
        found_blocks: list[str] = []
        # Search candidate files
        for py_file in self.repo_root.rglob("*.py"):
            if ".git" in py_file.parts or ".pytest_cache" in py_file.parts:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == target:
                            rel = py_file.relative_to(self.repo_root)
                            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
                            end_lineno = getattr(node, "end_lineno", node.lineno + 20)
                            segment = "\n".join(lines[node.lineno - 1 : end_lineno])
                            found_blocks.append(f"// Symbol `{target}` in {rel}:{node.lineno}\n{segment}")
                            break
            except Exception:
                continue
            if len(found_blocks) >= 2:
                break

        if not found_blocks:
            content = f"Symbol `{target}` not found in codebase AST."
        else:
            content = "\n\n".join(found_blocks)

        tokens = count_tokens(content)
        truncated = False
        if tokens > remaining_budget:
            content = truncate_to_tokens(content, remaining_budget)
            tokens = count_tokens(content)
            truncated = True

        return ResolvedReference(ContextRefType.SYMBOL, target, content, tokens, truncated)

    def _resolve_git(self, target: str, remaining_budget: int) -> ResolvedReference:
        """SPEC §6.2 line 2085: git:status, git:diff, or git log."""
        try:
            if target == "status":
                cmd = ["git", "status", "--short"]
            elif target == "diff":
                cmd = ["git", "diff", "--stat"]
            else:
                cmd = ["git", "log", "-n", "5", "--oneline", target]
            proc = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True, timeout=5)
            content = proc.stdout.strip() or "(empty git output)"
        except Exception as e:
            content = f"Error running git {target}: {e}"

        tokens = count_tokens(content)
        truncated = False
        if tokens > remaining_budget:
            content = truncate_to_tokens(content, remaining_budget)
            tokens = count_tokens(content)
            truncated = True

        return ResolvedReference(ContextRefType.GIT, target, content, tokens, truncated)

    def _resolve_diff(self, target: str, remaining_budget: int) -> ResolvedReference:
        """SPEC §6.2 line 2048: @diff:unstaged."""
        try:
            proc = subprocess.run(["git", "diff"], cwd=self.repo_root, capture_output=True, text=True, timeout=5)
            content = proc.stdout.strip() or "(no unstaged diff)"
        except Exception as e:
            content = f"Error resolving diff: {e}"

        tokens = count_tokens(content)
        truncated = False
        if tokens > remaining_budget:
            content = truncate_to_tokens(content, remaining_budget)
            tokens = count_tokens(content)
            truncated = True

        return ResolvedReference(ContextRefType.DIFF, target, content, tokens, truncated)

    def _resolve_url(self, target: str, remaining_budget: int) -> ResolvedReference:
        """SPEC §6.2 line 2049: @url:https://..."""
        content = f"URL reference: {target} (retrieval cached/external)"
        tokens = count_tokens(content)
        return ResolvedReference(ContextRefType.URL, target, content, tokens, False)

    def format_references_xml(self, refs: List[ResolvedReference]) -> str:
        """
        SPEC §6.2 lines 2104-2110:
        FUNCTION format_references_xml(refs: List[ResolvedReference]) -> string:
            blocks = []
            FOR EACH ref IN refs:
                blocks.append(f'''<context_ref type="{ref.ref_type.value}" target="{ref.target_path}">
    {ref.content}
    </context_ref>''')
            RETURN join("\n\n", blocks)
        """
        blocks: List[str] = []
        for ref in refs:
            blocks.append(
                f'<context_ref type="{ref.ref_type.value}" target="{ref.target_path}">\n'
                f"{ref.content}\n"
                f"</context_ref>"
            )
        return "\n\n".join(blocks)
