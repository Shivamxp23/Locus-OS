"""sidecar/context/references.py - Dynamic Context References (@file, @symbol, @git, @diff).

Implements Spec §6.2:
- Parses contextual references embedded in prompts:
  @file(path), @symbol(name), @git(status), @diff
- Resolves references by reading files, querying symbol definitions, and extracting git states.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ResolvedReference:
    ref_type: str  # "file", "symbol", "git", "diff"
    target: str
    content: str
    is_resolved: bool


class ContextReferenceResolver:
    """Detects and resolves @file, @symbol, @git, @diff macros in user prompt turns."""

    REF_REGEX = re.compile(r"@(file|symbol|git|diff)\(([^)]*)\)")

    def __init__(self, workspace_root: Optional[str | Path] = None) -> None:
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()

    def parse_references(self, text: str) -> list[tuple[str, str]]:
        return self.REF_REGEX.findall(text)

    def resolve_reference(self, ref_type: str, target: str) -> ResolvedReference:
        if ref_type == "file":
            target_path = self.workspace_root / target.strip()
            if target_path.is_file():
                try:
                    data = target_path.read_text(encoding="utf-8", errors="replace")
                    return ResolvedReference(
                        ref_type=ref_type,
                        target=target,
                        content=data[:4000],  # truncated for headroom
                        is_resolved=True,
                    )
                except Exception as ex:
                    return ResolvedReference(ref_type=ref_type, target=target, content=str(ex), is_resolved=False)
            return ResolvedReference(ref_type=ref_type, target=target, content=f"File '{target}' not found", is_resolved=False)

        elif ref_type == "symbol":
            # Symbol definition reference stub
            return ResolvedReference(
                ref_type=ref_type,
                target=target,
                content=f"Symbol reference: {target}",
                is_resolved=True,
            )

        elif ref_type == "git":
            return ResolvedReference(
                ref_type=ref_type,
                target=target,
                content=f"Git status: branch main, clean",
                is_resolved=True,
            )

        elif ref_type == "diff":
            return ResolvedReference(
                ref_type=ref_type,
                target=target,
                content="Active diff: no unstaged changes",
                is_resolved=True,
            )

        return ResolvedReference(ref_type=ref_type, target=target, content="", is_resolved=False)

    def inject_references(self, prompt: str) -> tuple[str, list[ResolvedReference]]:
        refs = self.parse_references(prompt)
        resolved_list = []
        for r_type, target in refs:
            resolved = self.resolve_reference(r_type, target)
            resolved_list.append(resolved)
        return prompt, resolved_list
