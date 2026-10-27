# US-80 Spec Traceability Matrix

## Feature
- ID: F-0047
- Title: Graceful Restart
- Spec Reference: §17.10 lines 3855-3926

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `GatewayLifecycleManager` with 30s connection draining loop | 3869-3890 | `sidecar/gateway/lifecycle.py:GatewayLifecycleManager` | `tests/unit/test_graceful_restart.py:test_lifecycle_manager_drain_and_timeout`, `tests/integration/test_graceful_restart_service.py:test_service_restart_drain` |
| Ingress adapter deregistration (`stop_receiving_new_messages`) | 3881 | `sidecar/gateway/lifecycle.py:BaseChannelAdapter`, `MockChannelAdapter` | `tests/unit/test_graceful_restart.py:test_swappable_channel_adapters` |
| In-memory session state serialization to disk (`~/.locus/sessions/recovery/{id}.json`) & recovery | 3892-3896 | `sidecar/gateway/lifecycle.py:GatewayLifecycleManager:snapshot_sessions`, `recover_sessions` | `tests/unit/test_graceful_restart.py:test_lifecycle_session_snapshotting_and_recovery`, `tests/integration/test_graceful_restart_service.py:test_service_restart_snapshot`, `test_service_restart_recovery` |
| Forensic telemetry recording (`log_shutdown_forensics`) | 3898-3905 | `sidecar/gateway/lifecycle.py:GatewayLifecycleManager:log_shutdown_forensics`, `ForensicRecord` | `tests/unit/test_graceful_restart.py:test_lifecycle_shutdown_forensics`, `tests/integration/test_graceful_restart_service.py:test_service_restart_initiate` |
| Modular Off-switches (`locus.graceful_restart.enabled`, `locus.gateway.graceful_restart.enabled`) returning HTTP 503 | 3922 | `sidecar/providers/graceful_restart.py:DefaultGracefulRestartProvider`, `sidecar/service.py` | `tests/unit/test_graceful_restart.py:test_graceful_restart_modular_off_switches`, `tests/integration/test_graceful_restart_service.py:test_service_restart_off_switches` |
| FastAPI Service Routes (`/gateway/restart/initiate`, `/drain`, `/snapshot`, `/recovery`, `/status`) | 3922 | `sidecar/service.py` | `tests/integration/test_graceful_restart_service.py` |
| Extension Client Contract | 3922 | `locus-extension/src/gateway/lifecycle.ts:GatewayLifecycleClient` | TypeScript contract and client |
