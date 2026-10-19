# US-27 Spec Trace (F-0035: Learning / Profiling / Reward Model)

## Covered Spec Sentences (§10.3, §10.5, §10.6-10.7, lines 2907-3000 & 6202-6305)
1. Line 2945: `recent = learning_buffer.drain_recent(window=30_minutes)` -> Implemented in `UnifiedLearningProvider.check_stability` and tested in `test_stability_detection_convergence` and `test_learning_candidate_and_stability_endpoints`.
2. Line 2951-2955: `// Score consistency: do all candidates agree? IF consistency > STABILITY_THRESHOLD: persist_stable_facet` -> Implemented in `check_stability` with consistency ratio threshold and tested in `test_stability_detection_convergence`.
3. Line 2959: `FUNCTION on_tool_call(tool_name, args, result, duration):` -> Implemented in `UnifiedLearningProvider.record_tool_usage` and `registerLearningHooks` and tested in `test_tool_usage_tracking` and `test_tool_usage_tracking_endpoint`.
4. Line 2974-2975: `profile_md = render_profile_markdown(facets); write_file(config.profile_path, profile_md)` -> Implemented in `generate_profile_markdown` and `_write_profile_document` and tested in `test_user_profile_markdown_generation` and `test_user_profile_endpoint`.
5. Line 6211: `Every Locus response gets a 👍 or 👎 reaction` -> Implemented in `UnifiedLearningProvider.record_reward_signal` and tested in `test_reward_signal_and_scoring_endpoints`.
6. Line 6234: `THRESHOLD: ≥ 0.6 for proactive output delivery` -> Implemented in `UnifiedLearningProvider.score_thought` and tested in `test_personal_reward_model_scoring` and `test_reward_signal_and_scoring_endpoints`.
7. Line 6255-6261: `edge.weight += 0.1 // access reinforcement; feedback == "positive" -> *1.3, "negative" -> *0.7` -> Implemented in `UnifiedLearningProvider.update_edge_weight` and tested in `test_hebbian_pathway_access_and_feedback` and `test_hebbian_update_endpoint`.
8. Line 6265: `edge.weight *= 0.95 // 5% weekly decay` -> Implemented in `UnifiedLearningProvider.apply_weekly_decay` and tested in `test_stdp_reinforcement_timing`.
9. Line 6271: `edge.weight *= 1.5 // strong reinforcement (<120000ms)` -> Implemented in `UnifiedLearningProvider.update_edge_weight` and tested in `test_stdp_reinforcement_timing`.
10. Line 6299: `IF pattern.confidence > 0.75 AND pattern.count > 2: promote_to_next_horizon(pattern)` -> Implemented in `UnifiedLearningProvider.detect_patterns` and tested in `test_multi_horizon_pattern_promotion` and `test_patterns_endpoint`.
11. Acceptance criteria: `Registers as a provider in sidecar/providers/ with modular off-switch locus.learning_profiling_reward_model.enabled returning 503.` -> Implemented and tested in `test_learning_off_switch` and `test_learning_off_switch_503`.
