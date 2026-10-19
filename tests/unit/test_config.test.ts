/**
 * SPEC §03 / F-0125 / US-05: Unit tests for TypeScript config accessor.
 */
import test from "node:test";
import assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { get, is_enabled, getConfig, isEnabled } from "../../locus-extension/src/config.ts";

test("TypeScript config accessor: get and is_enabled on nonexistent config", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "locus-ts-test-"));
  process.env["LOCUS_HOME"] = tmpDir;

  try {
    assert.strictEqual(get("locus.missing.key"), null);
    assert.strictEqual(get("locus.missing.key", "fallback"), "fallback");
    assert.strictEqual(is_enabled("locus.missing.flag"), false);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    delete process.env["LOCUS_HOME"];
  }
});

test("TypeScript config accessor: get and is_enabled with config.yaml", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "locus-ts-test-"));
  const cfgPath = path.join(tmpDir, "config.yaml");
  const yamlContent = `
locus:
  demo:
    value: 7
    active: true
    disabled: false
    name: "extension_test"
`;
  fs.writeFileSync(cfgPath, yamlContent, "utf-8");
  process.env["LOCUS_HOME"] = tmpDir;

  try {
    assert.strictEqual(get("locus.demo.value"), 7);
    assert.strictEqual(getConfig("locus.demo.value"), 7);
    assert.strictEqual(get("locus.demo.name"), "extension_test");
    assert.strictEqual(is_enabled("locus.demo.active"), true);
    assert.strictEqual(isEnabled("locus.demo.active"), true);
    assert.strictEqual(is_enabled("locus.demo.disabled"), false);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    delete process.env["LOCUS_HOME"];
  }
});
