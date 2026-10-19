/**
 * SPEC §03 / F-0125 / US-06: Node test for TypeScript ProviderRegistry.
 */
import test from "node:test";
import assert from "node:assert";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

import { ProviderRegistry, getRegistry } from "../../locus-extension/src/registry.ts";

test("TypeScript ProviderRegistry: singleton and basic registration", () => {
  const r1 = getRegistry();
  const r2 = getRegistry();
  assert.strictEqual(r1, r2, "getRegistry must return singleton");

  const reg = new ProviderRegistry();
  const dummy = { name: "dummy_tool" };
  reg.register("tools", "dummy", dummy);

  assert.strictEqual(reg.get("tools", "dummy"), dummy);
  assert.deepStrictEqual(reg.listProviders("tools"), ["dummy"]);
});

test("TypeScript ProviderRegistry: off-switch for tools and route check", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "locus-ts-reg-"));
  const prevHome = process.env["LOCUS_HOME"];
  process.env["LOCUS_HOME"] = tmpDir;

  try {
    const yamlContent = `
locus:
  tools:
    disabled_tool:
      enabled: false
    enabled_tool:
      enabled: true
`;
    fs.writeFileSync(path.join(tmpDir, "config.yaml"), yamlContent, "utf-8");

    const reg = new ProviderRegistry();

    // 1. Tool off-switch
    const okDisabled = reg.registerTool("disabled_tool", "locus.tools.disabled_tool.enabled", {});
    assert.strictEqual(okDisabled, false, "Disabled tool must NOT be registered");
    assert.ok(!reg.getRegisteredTools().includes("disabled_tool"));

    const okEnabled = reg.registerTool("enabled_tool", "locus.tools.enabled_tool.enabled", {});
    assert.strictEqual(okEnabled, true, "Enabled tool must be registered");
    assert.ok(reg.getRegisteredTools().includes("enabled_tool"));

    // 2. Route check answers 503
    const routeRes = reg.checkRouteAllowed("locus.tools.disabled_tool.enabled");
    assert.deepStrictEqual(routeRes, {
      status: 503,
      body: { disabled: "locus.tools.disabled_tool.enabled" },
    });

    const routeResEnabled = reg.checkRouteAllowed("locus.tools.enabled_tool.enabled");
    assert.strictEqual(routeResEnabled, null);
  } finally {
    if (prevHome !== undefined) {
      process.env["LOCUS_HOME"] = prevHome;
    } else {
      delete process.env["LOCUS_HOME"];
    }
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});
