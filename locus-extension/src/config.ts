/**
 * locus-extension/src/config.ts - Canonical configuration accessor for Locus OS (TypeScript side).
 *
 * Implements single source of truth for configuration (errata D-10):
 * - Reads LOCUS_HOME/config.yaml.
 * - get(path: string, defaultValue?: any): any
 * - is_enabled(path: string): boolean
 */

import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import * as YAML from "yaml";

let cachedData: Record<string, any> | null = null;
let cachedMtime: number = 0;

export function get_config_path(): string {
  const homeEnv = process.env.LOCUS_HOME;
  const home = homeEnv && homeEnv.trim() ? homeEnv.trim() : path.join(os.homedir(), ".locus");
  return path.join(home, "config.yaml");
}

export function clear_cache(): void {
  cachedData = null;
  cachedMtime = 0;
}

export function get(dotPath: string, defaultValue: any = null, customPath?: string): any {
  if (!dotPath || typeof dotPath !== "string") {
    return defaultValue;
  }

  if (dotPath.startsWith("env.")) {
    const envVar = dotPath.slice(4);
    const envVal = process.env[envVar];
    return envVal !== undefined ? envVal : defaultValue;
  }

  const configPath = customPath || get_config_path();

  try {
    if (fs.existsSync(configPath)) {
      const stat = fs.statSync(configPath);
      if (stat.mtimeMs !== cachedMtime || cachedData === null) {
        const raw = fs.readFileSync(configPath, "utf-8");
        const parsed = YAML.parse(raw);
        cachedData = parsed && typeof parsed === "object" ? parsed : {};
        cachedMtime = stat.mtimeMs;
      }
    } else {
      cachedData = {};
      cachedMtime = 0;
    }
  } catch {
    return defaultValue;
  }

  const parts = dotPath.split(".");
  let cur: any = cachedData;
  for (const part of parts) {
    if (cur === null || typeof cur !== "object" || !(part in cur)) {
      return defaultValue;
    }
    cur = cur[part];
  }

  return cur !== undefined && cur !== null ? cur : defaultValue;
}

export function is_enabled(dotPath: string, customPath?: string): boolean {
  const val = get(dotPath, false, customPath);
  if (typeof val === "boolean") {
    return val;
  }
  if (typeof val === "string") {
    return ["true", "1", "yes", "on"].includes(val.trim().toLowerCase());
  }
  if (typeof val === "number") {
    return val !== 0;
  }
  return false;
}
