# US-68 Spec Traceability Matrix

## Feature
- ID: F-0037
- Title: Injection Filter
- Spec Reference: §13.1 lines 3006-3140

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| Single-pass Unicode Normalization (leet-speak, Cyrillic, ZWSP, Fullwidth) | 3019-3040 | `sidecar/security/injection_filter.py:normalize_prompt` | `tests/unit/test_injection_filter.py:test_normalization_leet_and_cyrillic_folding`, `test_normalization_zwsp_stripping_and_detection` |
| Detection Rule: `override.ignore_previous` (0.44) | 3046-3047 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_rule_ignore_previous_instructions` |
| Detection Rule: `override.role_hijack` (0.30) | 3048-3049 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_rule_role_hijack` |
| Detection Rule: `exfiltrate.system_prompt` (0.42) | 3050-3051 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_rule_exfiltrate_system_prompt` |
| Detection Rule: `exfiltrate.secrets` (0.18) | 3052-3053 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_rule_exfiltrate_credentials_with_intent` |
| Detection Rule: `exfiltrate.credentials_with_intent` (0.46) | 3054-3057 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_rule_exfiltrate_credentials_with_intent` |
| Detection Rule: `tool.abuse` (0.30) | 3058-3059 | `sidecar/security/injection_filter.py:DETECTION_RULES` | `tests/unit/test_injection_filter.py:test_threshold_verdicts_allow_review_block` |
| Inline Heuristics & Classifier combinations | 3060-3072 | `sidecar/security/injection_filter.py:enforce_prompt_input` | `tests/unit/test_injection_filter.py:test_threshold_verdicts_allow_review_block` |
| Fixed Threshold Verdicts (0.55 Review, 0.70 Block) | 3073-3085 | `sidecar/security/injection_filter.py:enforce_prompt_input` | `tests/unit/test_injection_filter.py:test_threshold_verdicts_allow_review_block` |
| PII-Safe Audit Logging (SHA-256 prompt hash) | 3087-3092 | `sidecar/security/injection_filter.py:PromptEnforcementDecision` | `tests/unit/test_injection_filter.py:test_pii_safe_audit_hashing` |
| Tool Definition Scanning | 3093-3098 | `sidecar/security/injection_filter.py:scan_tool_definition` | `tests/unit/test_injection_filter.py:test_tool_definition_scanning` |
| Modular Off-switches (503) | 3105-3108 | `sidecar/providers/injection_filter.py:DefaultInjectionFilterProvider`, `sidecar/service.py` | `tests/unit/test_injection_filter.py:test_provider_modular_off_switches`, `tests/integration/test_injection_filter_service.py:test_service_injection_off_switches` |
| Service Routes (`/security/injection/enforce`, `/scan_tool`, `/normalize`) | 3100-3115 | `sidecar/service.py` | `tests/integration/test_injection_filter_service.py` |
| Extension Client Contract | 3100-3103 | `locus-extension/src/security/prompt-injection.ts` | TypeScript contract |
