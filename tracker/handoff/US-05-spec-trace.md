# US-05 Spec Trace

| spec line / source | the sentence quoted word for word | verdict | mechanism / file:line | test name |
|---|---|---|---|---|
| US-05 accept criteria 1 | "sidecar/config.py defines get(path, default=None) and is_enabled(path) and reads the config file at the location chosen in errata D-10; locus-extension/src/config.ts offers the same two functions over the same file." | LOCUS-NEW | sidecar/config.py:43, locus-extension/src/config.ts:80 | tests/unit/test_config.py::test_config_get_nested_values, tests/unit/test_config.test.ts |
| US-05 accept criteria 2 | "A missing key returns the default; is_enabled is false when the key is absent or false; no module outside the accessor reads os.environ, process.env or the config file directly (a unit test searches for it)." | LOCUS-NEW | sidecar/config.py:43, 60, locus-extension/src/config.ts:80, 99 | tests/unit/test_config.py::test_config_missing_file_returns_default, tests/unit/test_config.py::test_no_direct_env_or_config_reads_outside_accessor |
| US-05 accept criteria 3 | "py -3 -m sidecar.config get <path> prints the value (or the default), so any key can be checked by hand." | LOCUS-NEW | sidecar/config.py:73 | tests/unit/test_config.py::test_config_cli_get |
