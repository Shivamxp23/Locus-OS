# US-79 Spec Traceability Matrix

## Feature
- ID: F-0051
- Title: Computer Use / Screen
- Spec Reference: §16.1-16.2 + §20.1-20.3 lines 6496-6554

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `SCREEN INTELLIGENCE`: `analyze_screen(screenshot)` identifying buttons, links, text fields, dropdowns, checkboxes with coordinates | 6516-6526 | `sidecar/screen/screen_intelligence.py:ScreenIntelligence` | `tests/unit/test_screen_computer_use.py:test_screen_intelligence_element_analysis`, `tests/integration/test_screen_service.py:test_service_screen_analyze` |
| `DESKTOP COMPANION`: `control_desktop(action)` executing mouse_click, keyboard_type, capture_screen, focus_window | 6528-6538 | `sidecar/screen/desktop_control.py:BaseDesktopController`, `NativeDesktopController`, `MockDesktopController`, `sidecar/screen/manager.py:ComputerUseManager` | `tests/unit/test_screen_computer_use.py:test_desktop_controllers`, `tests/integration/test_screen_service.py:test_service_screen_control` |
| Screen Capture: `native.capture_screen()` display, region, and window capture | 6535 | `sidecar/screen/capture.py:DesktopScreenCaptureProvider`, `MockScreenCaptureProvider` | `tests/unit/test_screen_computer_use.py:test_screen_capture_providers`, `tests/integration/test_screen_service.py:test_service_screen_capture` |
| Integrated Computer Use Manager workflow execution | 6528-6538 | `sidecar/screen/manager.py:ComputerUseManager:execute_workflow` | `tests/unit/test_screen_computer_use.py:test_computer_use_manager_workflow`, `tests/integration/test_screen_service.py:test_service_screen_execute_workflow` |
| Modular Off-switches (`locus.screen.enabled`, `locus.computer_use.enabled`, `locus.desktop_control.enabled`) returning HTTP 503 | 6549 | `sidecar/providers/screen.py:DefaultScreenProvider`, `sidecar/service.py` | `tests/unit/test_screen_computer_use.py:test_screen_provider_modular_off_switches`, `tests/integration/test_screen_service.py:test_service_screen_off_switches` |
| FastAPI Service Routes (`/screen/capture`, `/control`, `/analyze`, `/execute`, `/status`) | 6549 | `sidecar/service.py` | `tests/integration/test_screen_service.py` |
| Extension Client Contract | 6549 | `locus-extension/src/screen/screen.ts:ScreenClient` | TypeScript contract and client |
