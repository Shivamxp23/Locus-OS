# US-61 Spec Trace — §7.1-7.9: Terminal Interface & Native @earendil-works/pi-tui Augmentation

Feature: F-0030 | Verdict: AUGMENT | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `CLASS LocusSettingsSelector EXTENDS Container:` | AUGMENT | locus-extension/src/ui/settings-selector.ts:14-72 | test_tui_dashboard_provider_off_switch |
| 2 | `items = [ NEW SettingItem("Deployment Topology", config.get("locus.topology")), NEW SettingItem("Primary LLM Provider", ...), ... ]` | AUGMENT | locus-extension/src/ui/settings-selector.ts:24-34 | test_tui_dashboard_provider_off_switch |
| 3 | `CLASS LocusFooterWidget EXTENDS Component:` | AUGMENT | locus-extension/src/ui/footer-widget.ts:11-75 | test_dashboard_renderer_three_column_layout |
| 4 | `left_col = f"DCS:{state.dcs} [{state.mode}] Faction:{state.active_faction}"` | AUGMENT | sidecar/display/dashboard.py:46-51, locus-extension/src/ui/footer-widget.ts:35-40 | test_dashboard_renderer_three_column_layout |
| 5 | `center_col = f"Mem:{state.neo4j_nodes}n / {state.neo4j_edges}e | LiveSync:OK"` | AUGMENT | sidecar/display/dashboard.py:53-58, locus-extension/src/ui/footer-widget.ts:42-45 | test_dashboard_renderer_three_column_layout |
| 6 | `right_col = f"Sidecar:{state.sidecar_latency_ms}ms | {state.model_name}"` | AUGMENT | sidecar/display/dashboard.py:60-63, locus-extension/src/ui/footer-widget.ts:47-49 | test_dashboard_renderer_three_column_layout |
| 7 | `row = format_three_column_row(left_col, center_col, right_col, width)` | AUGMENT | sidecar/display/dashboard.py:65-80 | test_dashboard_renderer_three_column_layout |
| 8 | `FUNCTION show_locus_doctor_overlay(ctx: ExtensionCommandContext):` | AUGMENT | locus-extension/src/ui/doctor-overlay.ts:16-73 | test_tui_dashboard_provider_off_switch |
| 9 | `pi.registerCommand("locus:setup", ...); pi.registerCommand("locus:settings", ...); pi.registerCommand("locus:doctor", ...)` | AUGMENT | locus-extension/src/index.ts:18-35 | test_tui_dashboard_provider_off_switch |
| 10 | `ctx.ui.setFooter((tui, theme, footerData) => NEW LocusFooterWidget(tui, theme, footerData))` | AUGMENT | locus-extension/src/index.ts:37-41 | test_dashboard_renderer_three_column_layout |
| 11 | `CursesDashboard and TUIDashboardEngine headless fallback` | AUGMENT | sidecar/display/dashboard.py:83-118, locus_cli/curses_ui.py:12-53 | test_dashboard_engine_render_row, test_curses_dashboard_render_once |
| 12 | `Swappable / off state: locus.tui_dashboard.enabled. Off -> 503 HTTP off-switch on dashboard endpoints.` | AUGMENT | sidecar/providers/tui_dashboard.py:27-58, sidecar/service.py:4638-4720 | test_tui_dashboard_provider_off_switch, test_service_tui_dashboard_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/display/dashboard.py` — §7.1-7.9 DashboardState, LocusDashboardRenderer, TUIDashboardEngine
- `sidecar/display/__init__.py` — display package exports
- `locus_cli/curses_ui.py` — CursesDashboard TUI implementation with headless fallback
- `sidecar/providers/tui_dashboard.py` — BaseTUIDashboardProvider & DefaultTUIDashboardProvider
- `sidecar/providers/__init__.py` — provider module exports
- `locus-extension/src/ui/footer-widget.ts` — TypeScript 3-column footer widget contract
- `locus-extension/src/ui/settings-selector.ts` — TypeScript settings modal contract
- `locus-extension/src/ui/doctor-overlay.ts` — TypeScript doctor overlay diagnostic contract
- `locus-extension/src/index.ts` — Extension command & footer registration
- `sidecar/service.py` — REST endpoints (`/display/dashboard/config`, `/state`, `/format`) with 503 off-switch
- `tests/unit/test_tui_dashboard.py` — unit tests for rows 1-7, 11, 12
- `tests/integration/test_tui_dashboard_service.py` — integration tests for rows 4-7, 12
- `tracker/features.yaml` — updated evidence for F-0030

No file or behaviour outside the spec trace.
