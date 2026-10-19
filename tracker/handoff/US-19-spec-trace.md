# US-19 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| SPEC §25.1 line 4566 | "FOUR FACTIONS: Health/Stability, Leverage/Money, Craft/Skills, Expression/Explore" | LOCUS-NEW | sidecar/life_os/factions.py:10-35, sidecar/providers/life_os.py:20-27 | tests/unit/test_life_os.py::test_four_factions_targets_and_lag_calculation |
| SPEC §25.1 line 4572 | "Weekly target allocation: Health 25% · Leverage 25% · Craft 30% · Expression 20%" | LOCUS-NEW | sidecar/life_os/factions.py:12-25 | tests/unit/test_life_os.py::test_four_factions_targets_and_lag_calculation |
| SPEC §25.2 line 4592 | "DCS = ((E + M + S) / 3) × (1 − ST/20)" | LOCUS-NEW | sidecar/life_os/dcs.py:15-55 | tests/unit/test_life_os.py::test_dcs_standard_calculation, tests/integration/test_life_os_service.py::test_life_os_service_endpoints |
| SPEC §25.2 line 4596 | "If no check-in today: apply staleness penalty (all scores × 0.9)" | LOCUS-NEW | sidecar/life_os/dcs.py:40-50 | tests/unit/test_life_os.py::test_dcs_staleness_penalty |
| SPEC §25.2 line 4597 | "If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert" | LOCUS-NEW | sidecar/life_os/dcs.py:28-36 | tests/unit/test_life_os.py::test_dcs_stale_fallback_after_three_days |
| SPEC §25.3 line 4614 | "Five Operating Modes: SURVIVAL, RECOVERY, NORMAL, DEEP WORK, PEAK" | LOCUS-NEW | sidecar/life_os/modes.py:12-65 | tests/unit/test_life_os.py::test_five_operating_modes_resolution, tests/integration/test_life_os_service.py::test_life_os_service_endpoints |
| SPEC §25.4 line 4636 | "TWS = (P × 0.4) + (U × 0.4) + (D × 0.2)" | LOCUS-NEW | sidecar/life_os/tws.py:20-65 | tests/unit/test_life_os.py::test_tws_base_formula_calculation, tests/integration/test_life_os_service.py::test_life_os_service_endpoints |
| SPEC §25.4 line 4641 | "LAG BONUS: faction Lag Score > 3h → TWS + 2, > 6h → TWS + 4, ahead → TWS − 1" | LOCUS-NEW | sidecar/life_os/tws.py:35-48 | tests/unit/test_life_os.py::test_tws_lag_bonuses_d1_option_a |
| SPEC §25.4 line 4646 | "POST-TASK LOG: A (actual time), Q (quality 1-10), R (reason if \|A − Est\| > 50%)" | LOCUS-NEW | sidecar/life_os/tws.py:75-105 | tests/unit/test_life_os.py::test_post_task_logging_and_reason_enforcement |
| SPEC §25.5 line 4664 | "Three-Layer Goal Stack (Outcome -> Project -> Task)" | LOCUS-NEW | sidecar/life_os/tws.py:50-65, sidecar/providers/life_os.py:15-19 | tests/unit/test_life_os.py::test_tws_multi_scale_scoring_rollup |
| SPEC §03 line 35 | "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}" | LOCUS-NEW | sidecar/service.py:255-330 | tests/unit/test_life_os.py::test_life_os_off_switch, tests/integration/test_life_os_service.py::test_life_os_service_modular_off_switch |
