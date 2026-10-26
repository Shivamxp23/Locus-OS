VERDICT: ACCEPT
Verifier: Claude Opus

## Guard output
```
LOCUS GUARD  mode=full  root=C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
[WARN] segment-size: docs/agent/11-agile-workflow.md is 8806 bytes (limit 7500). Segments must stay concentrated: split it.  (docs/agent/11-agile-workflow.md)
[WARN] spec-lint: 26 KNOWN spec defects still open (docs/agent/09-spec-errata.md). Agents must stop and ask when a task touches one.
[WARN] stale-locus-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-core: 40 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:415)
[WARN] stale-locus-extensions: 2 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:544)
[WARN] stale-locus-os-src-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-os-src-core: 11 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:1179)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:14)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:7095)

PASS: 0 FAIL, 9 WARN, 0 INFO  (3.8s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 55.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0030", "label": "INTEGRATED", "pct": 85, "flags": ["SPEC_CHANGED"], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| # | Acceptance Criterion | Code | Test | Status |
|---|---|---|---|---|
| 1 | Module implementing TUI / Dashboard per §7.1-7.9 created under sidecar/ or locus-extension/ | `sidecar/display/dashboard.py:1-125`, `locus_cli/curses_ui.py:1-55`, `locus-extension/src/ui/footer-widget.ts:1-75`, `locus-extension/src/ui/settings-selector.ts:1-74`, `locus-extension/src/ui/doctor-overlay.ts:1-75` | `tests/unit/test_tui_dashboard.py:1-122` | SATISFIED |
| 2 | Registers as a provider in sidecar/providers/ with modular off-switch locus.tui_dashboard.enabled returning 503 | `sidecar/providers/tui_dashboard.py:1-77`, `sidecar/service.py:4638-4720` | `tests/unit/test_tui_dashboard.py:112-122`, `tests/integration/test_tui_dashboard_service.py:70-85` | SATISFIED |
| 3 | Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `tests/unit/test_tui_dashboard.py:1-122` (6 unit tests), `tests/integration/test_tui_dashboard_service.py:1-85` (3 integration tests) | `tests/unit/test_tui_dashboard.py` + `tests/integration/test_tui_dashboard_service.py` (9 passed) | SATISFIED |

## Test attack result
Inverted the provider `is_available()` check in `sidecar/providers/tui_dashboard.py` (`return bool(...)` -> `return not bool(...)`).
Re-ran `pytest tests/unit/test_tui_dashboard.py::test_tui_dashboard_provider_off_switch`.
The test failed immediately with:
`AssertionError: assert False is True where False = is_available()`
Original code was restored.

## Findings
None. The implementation cleanly satisfies SPEC §7.1-7.9 requirements:
- `DashboardState` holds DCS, mode, faction, Neo4j nodes/edges, CouchDB LiveSync status, sidecar latency, and model name.
- `LocusDashboardRenderer` renders the 3-column footer row and full dashboard layout with proper width clipping.
- `TUIDashboardEngine` coordinates state caching, updates, and rendering.
- `CursesDashboard` provides a terminal curses UI with safe headless fallback.
- `DefaultTUIDashboardProvider` and FastAPI endpoints enforce the modular off-switch (`locus.tui_dashboard.enabled`) returning HTTP 503.
- `locus-extension` TypeScript contracts define the footer widget, settings selector, and doctor overlay with command registration.

## Not checked
Live terminal curses rendering was checked with synthetic screen/headless fallback; interactive keystroke capture in an active VT100 pseudo-terminal was not exercised.
