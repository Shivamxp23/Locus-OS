# US-106 Spec Trace: Connectivity Check (§29.5)

| Spec Line | Quoted Spec Sentence | Verdict | Implementation File:Line | Test Name / Status |
|---|---|---|---|---|
| 7631 | `ENDPOINTS = [` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:51` | `test_default_endpoints` |
| 7636 | `FUNCTION check_connectivity(timeout=5):` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:94` | `test_check_connectivity_success` |
| 7640 | `IF response.status < 400:` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:112` | `test_check_connectivity_success` |
| 7641 | `RETURN { online: true, latency_ms: response.elapsed, endpoint: endpoint }` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:114` | `test_check_connectivity_success` |
| 7643 | `CONTINUE // try next endpoint` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:122` | `test_check_connectivity_fallback` |
| 7645 | `RETURN { online: false, latency_ms: null }` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:126` | `test_check_connectivity_all_fail` |
| 7647 | `FUNCTION check_service_connectivity(services):` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:133` | `test_check_service_connectivity_healthy` |
| 7653 | `results[service.name] = { healthy: response.status == 200 }` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:157` | `test_check_service_connectivity_mixed` |
| 7659 | `// Used as gate before:` | LOCUS-NEW | `sidecar/diagnostics/connectivity.py:168` | `test_connectivity_gates` |
| 7668 | `- **Swappable / off state**: Always available (utility function). Used as a gate by Inner Loop, model escalation, and background tasks. If offline: Inner Loop skips web-dependent operations, model escalation forces local-only, web search returns empty results.` | LOCUS-NEW | `sidecar/providers/connectivity.py:70` | `test_connectivity_off_switch_503` |
