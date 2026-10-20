# US-40 Spec Trace: Git Tools (§3.7a)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2682 | `## Feature §3.7a: Git Tools` | AUGMENT | `sidecar/providers/git_tools.py:1` | `tests/unit/test_git_tools.py:25` |
| 2683 | `- **Verdict**: 🔄 AUGMENT · **Source**: Pi git.ts + Locus git_ops.py · **Repo vs .locus**: locus-os` | AUGMENT | `sidecar/git_tools.py:30`, `locus-extension/src/git-tools.ts:15` | `tests/unit/test_git_tools.py:35` |
| 2684 | `- **Swappable / off state**: locus.tools.git.enabled. Off → git tools unavailable.` | AUGMENT | `sidecar/git_tools.py:50`, `sidecar/service.py:1750` | `tests/unit/test_git_tools.py:120`, `tests/integration/test_git_tools_service.py:70` |
| 2685 | `- **Scope**: Pi has basic git. Augment with Locus' git_status, git_diff, git_commit.` | AUGMENT | `sidecar/git_tools.py:70-170` | `tests/unit/test_git_tools.py:50-100` |
| Criteria 1 | `Module implementing Git Tools per §3.7a: Git Tools created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/git_tools.py`, `locus-extension/src/git-tools.ts` | `tests/unit/test_git_tools.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.git_tools.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/git_tools.py:1`, `sidecar/service.py:1745` | `tests/unit/test_git_tools.py:120`, `tests/integration/test_git_tools_service.py:70` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_git_tools.py` | `tests/unit/test_git_tools.py:25-150` |
