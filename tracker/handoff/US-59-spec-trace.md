# US-59 Spec Trace — §6.2: Dynamic Context References (@file, @symbol, @git, @diff)

Feature: F-0028 | Verdict: AUGMENT | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `ContextRefType: FILE = "@file", DIR = "@dir", SYMBOL = "@symbol", GIT = "@git", DIFF = "@diff", URL = "@url"` | AUGMENT | sidecar/context/references.py:16-24 | test_context_ref_types_and_parser_regex |
| 2 | `ResolvedReference: ref_type: ContextRefType, target_path: string, content: string, token_count: int, truncated: bool` | AUGMENT | sidecar/context/references.py:27-55 | test_file_reference_resolution, test_token_budget_truncation |
| 3 | `REFERENCE PARSER REGEX: PATTERN = r"(@(file|dir|symbol|git|diff|url):([^\s\n]+))"` | AUGMENT | sidecar/context/references.py:72 | test_context_ref_types_and_parser_regex |
| 4 | `path, start_line, end_line = parse_path_and_lines(target)` | AUGMENT | sidecar/context/references.py:75-87 | test_context_ref_types_and_parser_regex, test_file_reference_resolution |
| 5 | `content = read_file_lines(path, start_line, end_line)` | AUGMENT | sidecar/context/references.py:145-167 | test_file_reference_resolution, test_service_context_references_resolve |
| 6 | `IF tokens > remaining_budget: content = truncate_to_tokens(content, remaining_budget); truncated = True` | AUGMENT | sidecar/context/references.py:65-70, 169-174 | test_token_budget_truncation |
| 7 | `ELIF ref_kind == "git": IF target == "status": content = git_status()` | AUGMENT | sidecar/context/references.py:221-237 | test_git_reference_resolution |
| 8 | `ELIF ref_kind == "symbol": content = ast_lookup_symbol(target)` | AUGMENT | sidecar/context/references.py:192-219 | test_symbol_reference_resolution |
| 9 | `clean_prompt = clean_prompt.replace(full_tag, f"[{ref_kind.upper()}: {target}]")` | AUGMENT | sidecar/context/references.py:138-140 | test_file_reference_resolution, test_service_context_references_resolve |
| 10 | `FUNCTION format_references_xml(refs: List[ResolvedReference]) -> string:` | AUGMENT | sidecar/context/references.py:257-273 | test_format_references_xml, test_service_context_references_format_xml |
| 11 | `Component: locus-os/src/core/context/references.ts -> locus-extension/src/context/references.ts` | AUGMENT | locus-extension/src/context/references.ts:1-75 | test_service_context_references_resolve |
| 12 | `Swappable / off state: locus.context.references.enabled. Off -> @ tags are treated as literal text; no file resolution occurs.` | AUGMENT | sidecar/providers/context_references.py:46-59, sidecar/service.py:4465-4545 | test_context_references_provider_off_switch, test_service_context_references_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/context/references.py` — §6.2 ContextReferenceResolver, ContextRefType, ResolvedReference, and parser regex
- `sidecar/context/__init__.py` — context package re-exports
- `sidecar/providers/context_references.py` — BaseContextReferenceProvider & DefaultContextReferenceProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/context/references.ts` — TypeScript contract
- `sidecar/service.py` — REST endpoints for context references with 503 off-switch
- `tests/unit/test_context_references.py` — unit tests for rows 1-10, 12
- `tests/integration/test_context_references_service.py` — integration tests for rows 5, 9, 10, 11, 12
- `tracker/features.yaml` — updated evidence for F-0028

No file or behaviour outside the spec trace.
