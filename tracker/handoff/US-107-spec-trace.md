# US-107 Spec Trace: Code Graph Analysis (§29.6)

| Spec Line | Quoted Spec Sentence | Verdict | Implementation File:Line | Test Name / Status |
|---|---|---|---|---|
| 7684 | `OpenHuman codegraph/analyzer.py (~200 lines): Scans project directories for source files, builds import/dependency graph, identifies module boundaries` | AUGMENT | `sidecar/codegraph/analyzer.py:45` | `test_scan_directory_discovers_source_files_and_ignores_excludes` |
| 7685 | `/graphify CLI: Full AST-based knowledge graph builder; produces graph.json at graphify-out/` | AUGMENT | `sidecar/codegraph/analyzer.py:321` | `test_graphify_integration_and_staleness` |
| 7690 | `files = scan_directory(project_path, extensions=[".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go"], exclude=["node_modules", ".git", "dist", "build", "__pycache__"])` | AUGMENT | `sidecar/codegraph/analyzer.py:72` | `test_scan_directory_discovers_source_files_and_ignores_excludes` |
| 7696 | `imports = extract_imports(file)` | AUGMENT | `sidecar/codegraph/analyzer.py:108` | `test_extract_imports_python`, `test_extract_imports_typescript_and_javascript`, `test_extract_imports_rust_and_go` |
| 7698 | `resolved = resolve_import_path(imported_module, file.dir); IF resolved: graph.add_edge(file.path, resolved.path, type="imports")` | AUGMENT | `sidecar/codegraph/analyzer.py:175` | `test_resolve_import_path_relative_and_module` |
| 7703 | `clusters = graph.find_connected_components()` | AUGMENT | `sidecar/codegraph/analyzer.py:223` | `test_find_connected_components` |
| 7706 | `importance = graph.calculate_centrality()` | AUGMENT | `sidecar/codegraph/analyzer.py:263` | `test_calculate_centrality` |
| 7709 | `entry_points: graph.find_roots() // files with no inbound imports` | AUGMENT | `sidecar/codegraph/analyzer.py:306` | `test_build_dependency_graph_and_roots` |
| 7717 | `scope_task_files(task_description, codebase_graph): identify minimal set of files that need editing, expand with transitive dependents (depth=2)` | AUGMENT | `sidecar/codegraph/analyzer.py:348` | `test_scope_task_files_with_transitive_dependents` |
| 7725 | `get_or_build_graph(project_path): if graphify-out/graph.json exists and age < 24h, load graphify graph; else analyze_codebase` | AUGMENT | `sidecar/codegraph/analyzer.py:392` | `test_graphify_integration_and_staleness` |
| 7738 | `Swappable / off state: locus.code_graph.enabled. Off -> returns 503.` | AUGMENT | `sidecar/providers/codegraph.py:70` | `test_modular_off_switch_returns_503` |
