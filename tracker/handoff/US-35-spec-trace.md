# US-35 Spec Trace: Anti-Hallucination Guard (Stage 10) (§2.6)

| Spec Line | Quoted Spec Sentence | Verdict | Implementation File:Line | Test Name |
|---|---|---|---|---|
| 1821 | `FUNCTION anti_hallucination_check(llm_response, context_forge_content):` | LOCUS-NEW | sidecar/anti_hallucination.py:65 | tests/unit/test_anti_hallucination.py::test_anti_hallucination_check_contract |
| 1822 | `Runs as afterToolCall hook OR as post-generation check` | LOCUS-NEW | locus-extension/src/anti-hallucination.ts:80 | tests/unit/test_anti_hallucination.py::test_after_tool_call_hook_dispatch |
| 1825 | `claims = extract_factual_claims(llm_response)` | LOCUS-NEW | sidecar/anti_hallucination.py:75 | tests/unit/test_anti_hallucination.py::test_extract_factual_claims |
| 1826 | `A "claim" is any statement about the user, their data, or their history; NOT opinions, advice, or external knowledge` | LOCUS-NEW | sidecar/anti_hallucination.py:90 | tests/unit/test_anti_hallucination.py::test_factual_claims_filter_opinions |
| 1832 | `IF NOT context_forge_content.contains_evidence_for(claim): ungrounded_claims.append(claim)` | LOCUS-NEW | sidecar/anti_hallucination.py:120 | tests/unit/test_anti_hallucination.py::test_grounding_evidence_check |
| 1838 | `IF config.anti_hallucination.mode == "strict": REJECT response; LOG to brain_errors (severity=2, type="hallucination"); RETURN { block: true, reason: "Response contained ungrounded claims" }` | LOCUS-NEW | sidecar/anti_hallucination.py:145 | tests/unit/test_anti_hallucination.py::test_strict_mode_rejects_and_logs |
| 1844 | `ELIF config.anti_hallucination.mode == "warn": response += "\n\n⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off."; LOG to brain_errors (severity=1, type="soft_hallucination")` | LOCUS-NEW | sidecar/anti_hallucination.py:165 | tests/unit/test_anti_hallucination.py::test_warn_mode_appends_caveat_and_logs |
| 1848 | `RETURN { block: false }` | LOCUS-NEW | sidecar/anti_hallucination.py:180 | tests/unit/test_anti_hallucination.py::test_clean_response_not_blocked |
| 1856 | `Component: locus/core/anti-hallucination.ts -> locus-extension/src/anti-hallucination.ts` | LOCUS-NEW | locus-extension/src/anti-hallucination.ts:1 | tests/unit/test_anti_hallucination.py::test_extension_component_exports |
| 1857 | `Integration: Runs in Pi's afterToolCall hook for the main LLM response (the "generate" tool result).` | LOCUS-NEW | locus-extension/src/anti-hallucination.ts:110 | tests/integration/test_anti_hallucination_service.py::test_hook_integration_endpoint |
