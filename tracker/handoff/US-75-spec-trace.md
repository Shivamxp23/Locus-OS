# US-75 Spec Traceability Matrix

## Feature
- ID: F-0043
- Title: Message Sanitization
- Spec Reference: §13.10 lines 3599-3668

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `SURROGATE_RE`: `[\uD800-\uDFFF]` regex matching lone surrogate code points | 3611 | `sidecar/security/sanitizer.py:SURROGATE_RE`, `locus-extension/src/security/message-sanitize.ts:SURROGATE_RE` | `tests/unit/test_message_sanitizer.py:test_sanitize_surrogate_replacement` |
| `sanitize_surrogates(text)`: replace invalid surrogates with U+FFFD; fast no-op when clean | 3614-3618 | `sidecar/security/sanitizer.py:sanitize_surrogates`, `locus-extension/src/security/message-sanitize.ts:sanitizeSurrogates` | `tests/unit/test_message_sanitizer.py:test_sanitize_clean_text_unchanged`, `test_sanitize_surrogate_replacement`, `tests/integration/test_message_sanitizer_service.py:test_service_sanitize_text` |
| `sanitize_structure_surrogates(payload)`: recursive dict/list walker replacing surrogates | 3620-3642 | `sidecar/security/sanitizer.py:sanitize_structure_surrogates`, `locus-extension/src/security/message-sanitize.ts:sanitizeStructureSurrogates` | `tests/unit/test_message_sanitizer.py:test_sanitize_structure_nested_dict_and_list`, `test_sanitize_structure_clean_returns_false_found`, `tests/integration/test_message_sanitizer_service.py:test_service_sanitize_structure` |
| `sanitize_messages(messages)`: sanitize message array, tool_calls, and reasoning_details | 3644-3653 | `sidecar/security/sanitizer.py:sanitize_messages`, `locus-extension/src/security/message-sanitize.ts:sanitizeMessages` | `tests/unit/test_message_sanitizer.py:test_sanitize_messages_array`, `tests/integration/test_message_sanitizer_service.py:test_service_sanitize_messages` |
| Modular Off-switches (`locus.message_sanitization.enabled`, `locus.security.message_sanitization.enabled`) | 3662 | `sidecar/providers/message_sanitizer.py:DefaultMessageSanitizerProvider`, `sidecar/service.py` | `tests/unit/test_message_sanitizer.py:test_provider_modular_off_switches`, `tests/integration/test_message_sanitizer_service.py:test_service_message_sanitizer_off_switches` |
| Service Routes (`/security/sanitize/text`, `/structure`, `/messages`) | 3655-3660 | `sidecar/service.py` | `tests/integration/test_message_sanitizer_service.py` |
| Extension Client Contract | 3656 | `locus-extension/src/security/message-sanitize.ts:MessageSanitizerClient` | TypeScript contract and client |
