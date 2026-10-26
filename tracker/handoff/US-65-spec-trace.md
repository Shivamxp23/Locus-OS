# US-65 Spec Trace — §9.9: Plugin LLM Sandboxing & Auxiliary Bridge

Feature: F-0034 | Verdict: LOCUS-NEW | Author model: Gemini Flash

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `Sandboxed secondary LLM execution bridge for extensions; protects main model's prompt cache and context` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:1-240, locus-extension/src/plugins/llm-bridge.ts:1-120 | test_plugin_llm_auxiliary_isolation_and_response |
| 2 | `CLASS PluginLLMBridge: plugin_id: string, token_quota_daily: int = 50000, tokens_used_today: int = 0` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:160-185 | test_plugin_llm_within_quota |
| 3 | `FUNCTION call_plugin_llm(messages: List[Dict], max_tokens: int = 500, temperature: float = 0.2) -> string:` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:220-270 | test_plugin_llm_within_quota, test_service_plugin_llm_generate |
| 4 | `1. Quota Enforcement: IF self.tokens_used_today + max_tokens > self.token_quota_daily: RAISE QuotaExceededError(f"Plugin {self.plugin_id} exceeded daily token limit.")` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:230-245 | test_plugin_llm_quota_exceeded |
| 5 | `2. Fetch Auxiliary Model (Cheap / Fast, e.g. DeepSeek V4 Flash or Gemini 2.5 Flash): aux_client = AuxiliaryClientPool.get_instance(task="plugin_execution")` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:140-158, 246-250 | test_plugin_llm_auxiliary_isolation_and_response |
| 6 | `3. Isolated Generation (Zero collision with main agent conversation cache): response = aux_client.generate(messages=messages, max_tokens=max_tokens, temperature=temperature, timeout=15.0)` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:60-135, 251-260 | test_plugin_llm_auxiliary_isolation_and_response, test_plugin_llm_timeout_fail_fast |
| 7 | `4. Record Usage: actual_tokens = response.usage.total_tokens; self.tokens_used_today += actual_tokens; log_plugin_usage(self.plugin_id, actual_tokens)` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:190-215, 261-268 | test_plugin_llm_persistent_usage_file, test_service_plugin_llm_usage |
| 8 | `Component: locus-os/src/plugins/llm-bridge.ts -> locus-extension/src/plugins/llm-bridge.ts` | LOCUS-NEW | locus-extension/src/plugins/llm-bridge.ts:1-125 | test_service_plugin_llm_generate |
| 9 | `Provider Interface: PluginLLMProvider` | LOCUS-NEW | sidecar/providers/plugin_llm.py:25-60 | test_plugin_llm_provider_swappable |
| 10 | `Repo vs .locus: code in locus-os (repo); per-plugin token usage tracked in .locus/usage/plugins.json.` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:175-215 | test_plugin_llm_persistent_usage_file |
| 11 | `Swappable / off state: locus.plugins.auxiliary_llm.enabled. Off -> plugins cannot make independent LLM calls.` | LOCUS-NEW | sidecar/providers/plugin_llm.py:72-83, sidecar/service.py:5030-5050 | test_plugin_llm_provider_is_available, test_service_plugin_llm_disabled_returns_503 |
| 12 | `STEAL VERBATIM: The per-plugin token quota enforcement, isolated auxiliary client invocation, and fail-fast 15s timeout.` | LOCUS-NEW | sidecar/plugins/llm_bridge.py:75-105, 230-260 | test_plugin_llm_timeout_fail_fast, test_plugin_llm_quota_exceeded |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/plugins/llm_bridge.py` — §9.9 PluginLLMBridge, AuxiliaryClient, AuxiliaryClientPool, QuotaExceededError, TokenUsage
- `sidecar/plugins/__init__.py` — re-exports
- `sidecar/providers/plugin_llm.py` — BasePluginLLMProvider & DefaultPluginLLMProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/plugins/llm-bridge.ts` — TypeScript PluginLLMBridgeClient contract
- `sidecar/service.py` — REST endpoints (`/plugins/llm/generate`, `/quota`, `/reset`, `/usage`) with 503 off-switch
- `tests/unit/test_plugin_llm.py` — unit tests for rows 1-7, 9-12
- `tests/integration/test_plugin_llm_service.py` — integration tests for rows 3, 7, 8, 11
- `tracker/features.yaml` — updated evidence for F-0034

No file or behaviour outside the spec trace.
