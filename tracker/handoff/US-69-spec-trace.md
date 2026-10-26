# US-69 Spec Traceability Matrix

## Feature
- ID: F-0107
- Title: File Safety
- Spec Reference: §13.2 lines 3141-3165

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `cwd_jail`: confine file operations to project root + allowed paths | 3148 | `sidecar/security/file_safety.py:CwdJail` | `tests/unit/test_file_safety.py:test_cwd_jail_allowed_inside_root`, `test_cwd_jail_path_traversal_blocked`, `test_cwd_jail_null_byte_blocked` |
| `file_state tracking`: track file modifications across tool calls | 3149 | `sidecar/security/file_safety.py:FileStateTracker`, `FileStateRecord` | `tests/unit/test_file_safety.py:test_file_state_tracking`, `tests/integration/test_file_safety_service.py:test_service_file_record_and_history` |
| `BLOCKED_PATTERNS`: layered safety blocking sensitive files | 3150 | `sidecar/security/file_safety.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_file_safety.py:test_blocked_pattern_git_write`, `test_blocked_pattern_env_and_keys` |
| Modular Off-switches (`locus.file_safety.enabled`, `locus.security.file_safety.enabled`) | 3158-3160 | `sidecar/providers/file_safety.py:DefaultFileSafetyProvider`, `sidecar/service.py` | `tests/unit/test_file_safety.py:test_file_safety_provider_off_switches`, `tests/integration/test_file_safety_service.py:test_service_file_safety_off_switches` |
| Service Routes (`/security/file/validate`, `/record`, `/history`) | 3152-3160 | `sidecar/service.py` | `tests/integration/test_file_safety_service.py` |
| Extension Client Contract | 3153-3155 | `locus-extension/src/security/file-safety.ts:FileSafetyClient` | TypeScript contract |
