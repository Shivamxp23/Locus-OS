# US-60 Spec Trace — §6.3: Coding Context Engine (Repo Map, AST Index, Active Diff)

Feature: F-0029 | Verdict: AUGMENT | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `DATA STRUCTURES: WorkspaceCodingState: repo_root: string, active_branch: string, dirty_files: List[string], staged_diff_stat: string, unstaged_diff_stat: string, repo_map_snippet: string, recent_edits: List[string]` | AUGMENT | sidecar/context/coding_context.py:19-42 | test_workspace_coding_state_data_structure |
| 2 | `FUNCTION generate_coding_context(repo_path: string, token_budget: int = 500) -> WorkspaceCodingState:` | AUGMENT | sidecar/context/coding_context.py:204-219 | test_generate_coding_context_layer, test_service_coding_context_state_and_format |
| 3 | `state.active_branch = git_current_branch(repo_path)` | AUGMENT | sidecar/context/coding_context.py:53-78, 208 | test_git_metadata_collector |
| 4 | `state.dirty_files = git_dirty_files(repo_path)` | AUGMENT | sidecar/context/coding_context.py:80-88, 209 | test_git_metadata_collector |
| 5 | `state.staged_diff_stat = git_diff_stat(repo_path, staged=True)` | AUGMENT | sidecar/context/coding_context.py:90-95, 210 | test_git_metadata_collector |
| 6 | `state.unstaged_diff_stat = git_diff_stat(repo_path, staged=False)` | AUGMENT | sidecar/context/coding_context.py:90-95, 211 | test_git_metadata_collector |
| 7 | `tags = extract_ast_tags(repo_path)  // Tree-sitter extraction of classes, functions, interfaces` | AUGMENT | sidecar/context/coding_context.py:115-146 | test_ast_tag_extraction_and_pagerank |
| 8 | `call_graph = build_call_graph(tags); ranked_files = compute_pagerank(call_graph)` | AUGMENT | sidecar/context/coding_context.py:148-181 | test_ast_tag_extraction_and_pagerank |
| 9 | `IF current_tokens + tree_tokens > token_budget: BREAK` | AUGMENT | sidecar/context/coding_context.py:197-200 | test_repo_map_budget_enforcement |
| 10 | `FUNCTION format_coding_context_layer(state: WorkspaceCodingState) -> string:` | AUGMENT | sidecar/context/coding_context.py:221-236 | test_generate_coding_context_layer, test_service_coding_context_state_and_format |
| 11 | `Component: locus-os/src/core/context/coding-context.ts -> locus-extension/src/context/coding-context.ts` | AUGMENT | locus-extension/src/context/coding-context.ts:1-65 | test_service_coding_context_state_and_format |
| 12 | `Swappable / off state: locus.context.coding_map.enabled. Off -> coding context omitted from prompt; agent relies on explicit tool lookups.` | AUGMENT | sidecar/providers/coding_context.py:44-59, sidecar/service.py:4548-4630 | test_coding_context_provider_off_switch, test_service_coding_context_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/context/coding_context.py` — §6.3 CodingContextEngine, WorkspaceCodingState, ASTRepoMapGenerator, GitMetadataCollector
- `sidecar/context/__init__.py` — context package re-exports
- `sidecar/providers/coding_context.py` — BaseCodingContextProvider & DefaultCodingContextProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/context/coding-context.ts` — TypeScript contract
- `sidecar/service.py` — REST endpoints for coding context with 503 off-switch
- `tests/unit/test_coding_context.py` — unit tests for rows 1-10, 12
- `tests/integration/test_coding_context_service.py` — integration tests for rows 2, 10, 11, 12
- `tracker/features.yaml` — updated evidence for F-0029

No file or behaviour outside the spec trace.
