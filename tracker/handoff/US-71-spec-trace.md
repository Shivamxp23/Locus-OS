# US-71 Spec Traceability Matrix

## Feature
- ID: F-0109
- Title: Approval Gate
- Spec Reference: §13.5 lines 3333-3365

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `queue_approval(task_id, changes, ttl=600)` | 3343-3345 | `sidecar/security/approval_store.py:ApprovalStore.queue_approval` | `tests/unit/test_approval_gate.py:test_queue_approval_creates_pending_request`, `test_queue_approval_default_ttl` |
| `wait_for_approval(task_id, ttl)` | 3347-3353 | `sidecar/security/approval_store.py:ApprovalStore.wait_for_approval` | `tests/unit/test_approval_gate.py:test_wait_for_approval_resolves_approved`, `test_wait_for_approval_resolves_rejected`, `test_wait_for_approval_times_out` |
| `status == "approved" -> true` | 3350 | `sidecar/security/approval_store.py:resolve_approval` | `tests/unit/test_approval_gate.py:test_resolve_approval_to_approved`, `tests/integration/test_approval_gate_service.py:test_service_approval_lifecycle` |
| `status == "rejected" -> false` | 3351 | `sidecar/security/approval_store.py:resolve_approval` | `tests/unit/test_approval_gate.py:test_resolve_approval_to_rejected`, `tests/integration/test_approval_gate_service.py:test_service_approval_rejection` |
| `TTL expired = auto-reject -> false` | 3353 | `sidecar/security/approval_store.py:ApprovalRequest.check_expiration` | `tests/unit/test_approval_gate.py:test_ttl_expiration_auto_reject` |
| Runtime-only state (not persisted to `.locus`) | 3357 | `sidecar/security/approval_store.py:ApprovalStore` (in-memory) | `tests/unit/test_approval_gate.py:test_list_pending_only_returns_active_unexpired` |
| Modular Off-switches (`locus.approval_gate.enabled`, `locus.security.approval_gate.enabled`) | 3358 | `sidecar/providers/approval_gate.py:DefaultApprovalGateProvider`, `sidecar/service.py` | `tests/unit/test_approval_gate.py:test_provider_modular_off_switches`, `tests/integration/test_approval_gate_service.py:test_service_approval_off_switches` |
| Service Routes (`/security/approval/request`, `/status`, `/resolve`, `/wait`, `/pending`) | 3356-3359 | `sidecar/service.py` | `tests/integration/test_approval_gate_service.py` |
| Extension Client Contract | 3356 | `locus-extension/src/security/approval-gate.ts:ApprovalGateClient` | TypeScript contract |
