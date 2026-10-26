# US-73 Spec Traceability Matrix

## Feature
- ID: F-0041
- Title: Data Redaction
- Spec Reference: §13.8 lines 3438-3512

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `SENSITIVE_QUERY_PARAMS`: ["access_token", "token", "api_key", "secret", ...] | 3456-3460 | `sidecar/security/redact.py:SENSITIVE_QUERY_PARAMS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_query_parameters`, `tests/integration/test_data_redaction_service.py:test_service_redact_text` |
| `SENSITIVE_BODY_KEYS`: ["access_token", "token", "api_key", "password", ...] | 3462-3466 | `sidecar/security/redact.py:SENSITIVE_BODY_KEYS` | `tests/unit/test_data_redaction.py:test_redact_structure_nested_dict_and_list`, `tests/integration/test_data_redaction_service.py:test_service_redact_structure` |
| `KEY_PATTERNS`: OpenAI regex (`/sk-[a-zA-Z0-9]{20,}/`) | 3470 | `sidecar/security/redact.py:KEY_PATTERNS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_openai_key` |
| `KEY_PATTERNS`: Anthropic regex (`/sk-ant-[a-zA-Z0-9-]{20,}/`) | 3471 | `sidecar/security/redact.py:KEY_PATTERNS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_anthropic_key` |
| `KEY_PATTERNS`: Google regex (`/AIza[a-zA-Z0-9_-]{35}/`) | 3472 | `sidecar/security/redact.py:KEY_PATTERNS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_google_key` |
| `KEY_PATTERNS`: GitHub regex (`/ghp_[a-zA-Z0-9]{30,}/`) | 3473 | `sidecar/security/redact.py:KEY_PATTERNS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_github_token` |
| `KEY_PATTERNS`: Slack regex (`/xoxb-[0-9-]+/`) & AWS / Bearer / JWT | 3474-3475 | `sidecar/security/redact.py:KEY_PATTERNS` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_slack_and_aws_keys`, `test_redact_sensitive_text_jwt_and_bearer` |
| `mask_token(token)`: <18 chars fully masked, >=18 chars first 6 + last 4 | 3491-3496 | `sidecar/security/redact.py:mask_token`, `locus-extension/src/security/redact.ts:maskToken` | `tests/unit/test_data_redaction.py:test_mask_token_short_token`, `test_mask_token_long_token` |
| `redact_sensitive_text(text)` | 3478-3489 | `sidecar/security/redact.py:DataRedactor.redact_sensitive_text` | `tests/unit/test_data_redaction.py:test_redact_sensitive_text_openai_key`, `test_custom_redaction_patterns` |
| `redact_structure(payload)`: recursive dict/list walker | 3497-3502 | `sidecar/security/redact.py:DataRedactor.redact_structure` | `tests/unit/test_data_redaction.py:test_redact_structure_nested_dict_and_list`, `test_redact_structure_preserves_benign_fields`, `tests/integration/test_data_redaction_service.py:test_service_redact_structure` |
| Modular Off-switches (`locus.data_redaction.enabled`, `locus.security.data_redaction.enabled`) | 3480 | `sidecar/providers/data_redaction.py:DefaultDataRedactionProvider`, `sidecar/service.py` | `tests/unit/test_data_redaction.py:test_provider_modular_off_switches`, `tests/integration/test_data_redaction_service.py:test_service_data_redaction_off_switches` |
| Service Routes (`/security/redact/text`, `/structure`, `/patterns`) | 3505 | `sidecar/service.py` | `tests/integration/test_data_redaction_service.py` |
| Extension Client Contract | 3505 | `locus-extension/src/security/redact.ts:DataRedactionClient` | TypeScript contract and `createAfterToolCallHook` |
