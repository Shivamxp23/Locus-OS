# US-72 Spec Traceability Matrix

## Feature
- ID: F-0040
- Title: Shell Blocklist
- Spec Reference: §13.7 lines 3374-3437

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `SENSITIVE_HOME_DIRS`: [".ssh", ".aws", ".gnupg", ".kube", ...] | 3388 | `sidecar/security/shell_policy.py:SENSITIVE_HOME_DIRS` | `tests/unit/test_shell_blocklist.py:test_sensitive_home_dirs_read_blocked` |
| `SENSITIVE_HOME_FILES`: [".ssh/authorized_keys", ".bashrc", ...] | 3389 | `sidecar/security/shell_policy.py:SENSITIVE_HOME_FILES` | `tests/unit/test_shell_blocklist.py:test_sensitive_home_files_read_blocked` |
| `is_read_blocked(path)` | 3396-3402 | `sidecar/security/shell_policy.py:ShellPolicyEngine.is_read_blocked` | `tests/unit/test_shell_blocklist.py:test_sensitive_home_dirs_read_blocked`, `test_sensitive_home_files_read_blocked` |
| `is_write_denied(path)` | 3404-3409 | `sidecar/security/shell_policy.py:ShellPolicyEngine.is_write_denied` | `tests/unit/test_shell_blocklist.py:test_write_denied_outside_trust_boundary`, `tests/integration/test_shell_blocklist_service.py:test_service_shell_check_path` |
| `BLOCKED_SHELL_PATTERNS`: destructive root/home wipe | 3412 | `sidecar/security/shell_policy.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_shell_blocklist.py:test_blocked_patterns_destructive_rm`, `tests/integration/test_shell_blocklist_service.py:test_service_shell_check` |
| `BLOCKED_SHELL_PATTERNS`: fork bomb | 3413 | `sidecar/security/shell_policy.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_shell_blocklist.py:test_blocked_patterns_fork_bomb` |
| `BLOCKED_SHELL_PATTERNS`: unsafe permissions (chmod -R 777) | 3414 | `sidecar/security/shell_policy.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_shell_blocklist.py:test_blocked_patterns_unsafe_permissions` |
| `BLOCKED_SHELL_PATTERNS`: pipe-to-shell (curl \| sh) | 3415 | `sidecar/security/shell_policy.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_shell_blocklist.py:test_blocked_patterns_pipe_to_shell`, `tests/integration/test_shell_blocklist_service.py:test_service_shell_check` |
| `BLOCKED_SHELL_PATTERNS`: privilege escalation (sudo rm/chmod) | 3416 | `sidecar/security/shell_policy.py:DEFAULT_BLOCKED_PATTERNS` | `tests/unit/test_shell_blocklist.py:test_blocked_patterns_privilege_escalation` |
| `check_shell_command(command)` | 3419-3423 | `sidecar/security/shell_policy.py:ShellPolicyEngine.check_shell_command` | `tests/unit/test_shell_blocklist.py:test_benign_commands_allowed`, `test_custom_pattern_blocklist` |
| Modular Off-switches (`locus.shell_blocklist.enabled`, `locus.security.shell_blocklist.enabled`) | 3428 | `sidecar/providers/shell_blocklist.py:DefaultShellBlocklistProvider`, `sidecar/service.py` | `tests/unit/test_shell_blocklist.py:test_provider_modular_off_switches`, `tests/integration/test_shell_blocklist_service.py:test_service_shell_blocklist_off_switches` |
| Service Routes (`/security/shell/check`, `/check_path`, `/patterns`) | 3426-3430 | `sidecar/service.py` | `tests/integration/test_shell_blocklist_service.py` |
| Extension Client Contract | 3426 | `locus-extension/src/security/shell-policy.ts:ShellPolicyClient` | TypeScript contract |
