/**
 * SPEC §03 / F-0125 / US-05: Single configuration accessor for TypeScript locus-extension.
 * Reads LOCUS_HOME/config.yaml (default ~/.locus/config.yaml per errata D-10).
 * No module outside this accessor may read process.env or config.yaml directly.
 */
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

export function getLocusHome(): string {
  const envHome = process.env["LOCUS_HOME"];
  if (envHome && envHome.trim().length > 0) {
    return path.resolve(envHome.trim());
  }
  return path.join(os.homedir(), ".locus");
}

export function getConfigPath(): string {
  return path.join(getLocusHome(), "config.yaml");
}

/**
 * Basic recursive YAML parser for nested key-value mappings.
 */
function parseSimpleYaml(content: string): Record<string, any> {
  const result: Record<string, any> = {};
  const lines = content.split(/\r?\n/);
  const stack: { indent: number; obj: Record<string, any> }[] = [{ indent: -1, obj: result }];

  for (const rawLine of lines) {
    const line = rawLine.replace(/#.*$/, ""); // strip comments
    if (!line.trim()) continue;

    const indent = rawLine.search(/\S/);
    const trimmed = line.trim();

    const colonIdx = trimmed.indexOf(":");
    if (colonIdx === -1) continue;

    const key = trimmed.slice(0, colonIdx).trim();
    const rawVal = trimmed.slice(colonIdx + 1).trim();

    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
      stack.pop();
    }
    const current = stack[stack.length - 1].obj;

    if (rawVal.length === 0) {
      // Nested object
      const childObj: Record<string, any> = {};
      current[key] = childObj;
      stack.push({ indent, obj: childObj });
    } else {
      let val: any = rawVal;
      if (val === "true" || val === "True") val = true;
      else if (val === "false" || val === "False") val = false;
      else if (val === "null" || val === "None") val = null;
      else if (!isNaN(Number(val)) && !isNaN(parseFloat(val))) val = Number(val);
      else if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      current[key] = val;
    }
  }

  return result;
}

function loadRawConfig(): Record<string, any> {
  const cfgPath = getConfigPath();
  if (!fs.existsSync(cfgPath)) {
    return {};
  }
  try {
    const content = fs.readFileSync(cfgPath, "utf-8");
    return parseSimpleYaml(content);
  } catch {
    return {};
  }
}

/**
 * Get configuration value by dot-separated path.
 */
export function get(configPath: string, defaultValue: any = null): any {
  if (!configPath) return defaultValue;
  const data = loadRawConfig();
  const parts = configPath.trim().split(".");
  let cur: any = data;

  for (const part of parts) {
    if (cur !== null && typeof cur === "object" && part in cur) {
      cur = cur[part];
    } else {
      return defaultValue;
    }
  }

  return cur !== undefined && cur !== null ? cur : defaultValue;
}

export const getConfig = get;

/**
 * Check if a configuration flag is enabled.
 */
export function is_enabled(configPath: string): boolean {
  const val = get(configPath, false);
  if (typeof val === "boolean") return val;
  if (typeof val === "number") return val !== 0;
  if (typeof val === "string") {
    const lower = val.trim().toLowerCase();
    return lower === "true" || lower === "1" || lower === "yes" || lower === "on";
  }
  return false;
}

export const isEnabled = is_enabled;
