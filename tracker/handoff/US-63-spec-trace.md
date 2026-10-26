# US-63 Spec Trace — §9.2: Skill System & Multi-Source Marketplace

Feature: F-0119 | Verdict: LOCUS-NEW | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `DATA STRUCTURES: SkillManifest: name: string, description: string, version: string, author: string, repository_url: string, dependencies: List[string], env_vars_required: List[string]` | LOCUS-NEW | sidecar/skills/marketplace.py:27-59, locus-extension/src/skills/marketplace.ts:7-16 | test_skill_manifest_data_structure |
| 2 | `FUNCTION install_skill_from_marketplace(source: string, skill_name: string) -> bool:` | LOCUS-NEW | sidecar/skills/marketplace.py:126-157 | test_skill_marketplace_install_and_list |
| 3 | `INDEX_URLS = { "pi-gallery": ..., "anthropic": ..., "claude-skills": ..., "openai": ..., "lobehub": ... }` | LOCUS-NEW | sidecar/skills/marketplace.py:20-26 | test_skill_marketplace_index_urls |
| 4 | `target_url = INDEX_URLS[source] + skill_name + "/manifest.json"` | LOCUS-NEW | sidecar/skills/marketplace.py:80-85 | test_skill_marketplace_build_manifest_url_and_fetch |
| 5 | `manifest = http_get_json(target_url)` | LOCUS-NEW | sidecar/skills/marketplace.py:87-110 | test_skill_marketplace_build_manifest_url_and_fetch |
| 6 | `FOR EACH env_var IN manifest.env_vars_required: IF env_var NOT IN env: PROMPT_USER(f"Skill {skill_name} requires {env_var}. Configure now?")` | LOCUS-NEW | sidecar/skills/marketplace.py:112-124 | test_skill_marketplace_prerequisites_validation |
| 7 | `install_dir = f"~/.locus/skills/{skill_name}/"` | LOCUS-NEW | sidecar/skills/marketplace.py:133-134 | test_skill_marketplace_install_and_list |
| 8 | `download_and_extract_bundle(manifest.bundle_url, install_dir)` | LOCUS-NEW | sidecar/skills/marketplace.py:136-154 | test_skill_marketplace_install_and_list |
| 9 | `RETURN True` | LOCUS-NEW | sidecar/skills/marketplace.py:156 | test_skill_marketplace_install_and_list |
| 10 | `Component: locus-os/src/skills/marketplace.ts -> locus-extension/src/skills/marketplace.ts` | LOCUS-NEW | locus-extension/src/skills/marketplace.ts:1-75 | test_service_skill_marketplace_sources_and_manifest |
| 11 | `Swappable / off state: locus.skill_system_multi_source_marketplace.enabled. Off -> 503 HTTP off-switch on marketplace endpoints.` | LOCUS-NEW | sidecar/providers/skill_marketplace.py:46-60, sidecar/service.py:4850-4940 | test_skill_marketplace_provider_off_switch, test_service_skill_marketplace_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/skills/marketplace.py` — §9.2 SkillManifest, INDEX_URLS, and SkillMarketplaceEngine
- `sidecar/skills/__init__.py` — skills package exports
- `sidecar/providers/skill_marketplace.py` — BaseSkillMarketplaceProvider & DefaultSkillMarketplaceProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/skills/marketplace.ts` — TypeScript SkillMarketplaceClient contract
- `sidecar/service.py` — REST endpoints (`/skills/marketplace/sources`, `/manifest`, `/install`, `/installed`) with 503 off-switch
- `tests/unit/test_skill_marketplace.py` — unit tests for rows 1-9, 11
- `tests/integration/test_skill_marketplace_service.py` — integration tests for rows 2, 5, 8, 10, 11
- `tracker/features.yaml` — updated evidence for F-0119

No file or behaviour outside the spec trace.
