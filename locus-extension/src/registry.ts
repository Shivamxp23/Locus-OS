/**
 * locus-extension/src/registry.ts - Universal Provider Registry for Locus OS (TypeScript side).
 *
 * Implements the Universal Provider Pattern (modularity spec):
 * - ProviderRegistry and get_registry() / getRegistry()
 * - register(interface, name, provider, is_default)
 * - get(interface, name, config_key)
 * - Tool & job suppression when feature is disabled
 * - Provider swap via locus.<area>.<feature>.provider
 * - Health checks: health_check() -> { status, latency_ms, error }
 */

import { get as config_get, is_enabled as config_is_enabled } from "./config.ts";

export interface HealthStatus {
  status: "ok" | "degraded" | "down" | "disabled";
  latency_ms: number;
  error?: string | null;
}

export class FeatureDisabledError extends Error {
  configKey: string;

  constructor(configKey: string) {
    super(`Feature is disabled by config: ${configKey}`);
    this.name = "FeatureDisabledError";
    this.configKey = configKey;
  }
}

export class BaseProvider {
  name: string = "base";

  initialize(options?: Record<string, any>): void | Promise<void> {}

  shutdown(): void | Promise<void> {}

  health_check(): HealthStatus | Promise<HealthStatus> {
    return { status: "ok", latency_ms: 0.0, error: null };
  }
}

export class ProviderRegistry {
  private providers: Map<string, any> = new Map();
  private defaults: Map<string, string> = new Map();
  private tools: Map<string, any[]> = new Map();
  private jobs: Map<string, any[]> = new Map();

  private makeKey(interfaceName: string, name: string): string {
    return `${interfaceName}:${name}`;
  }

  public clear(): void {
    this.providers.clear();
    this.defaults.clear();
    this.tools.clear();
    this.jobs.clear();
  }

  public register(
    interfaceName: string,
    name: string,
    provider: any,
    isDefault: boolean = false
  ): void {
    const key = this.makeKey(interfaceName, name);
    this.providers.set(key, provider);
    if (isDefault || !this.defaults.has(interfaceName)) {
      this.defaults.set(interfaceName, name);
    }
  }

  public get(
    interfaceName: string,
    name?: string,
    configKey?: string,
    customConfigPath?: string
  ): any {
    if (configKey) {
      const enabledKey = configKey.endsWith(".enabled") ? configKey : `${configKey}.enabled`;
      if (!config_is_enabled(enabledKey, customConfigPath)) {
        throw new FeatureDisabledError(enabledKey);
      }
    }

    let providerName = name;
    if (!providerName && configKey) {
      const baseKey = configKey.endsWith(".enabled")
        ? configKey.slice(0, -8)
        : configKey;
      providerName = config_get(`${baseKey}.provider`, null, customConfigPath);
    }

    if (!providerName) {
      providerName = this.defaults.get(interfaceName);
    }

    if (!providerName) {
      throw new Error(`No default provider registered for interface '${interfaceName}'`);
    }

    const key = this.makeKey(interfaceName, providerName);
    if (!this.providers.has(key)) {
      throw new Error(`Provider '${providerName}' not registered for interface '${interfaceName}'`);
    }

    const entry = this.providers.get(key);
    // If it's a constructor/class, instantiate it
    if (typeof entry === "function" && entry.prototype) {
      const instance = new entry();
      this.providers.set(key, instance);
      return instance;
    }

    return entry;
  }

  public register_tool(configKey: string, toolDef: any): void {
    const list = this.tools.get(configKey) || [];
    list.push(toolDef);
    this.tools.set(configKey, list);
  }

  public registerTool(configKey: string, toolDef: any): void {
    this.register_tool(configKey, toolDef);
  }

  public get_active_tools(customConfigPath?: string): any[] {
    const active: any[] = [];
    for (const [configKey, toolList] of this.tools.entries()) {
      const enabledKey = configKey.endsWith(".enabled") ? configKey : `${configKey}.enabled`;
      if (config_is_enabled(enabledKey, customConfigPath)) {
        active.push(...toolList);
      }
    }
    return active;
  }

  public getActiveTools(customConfigPath?: string): any[] {
    return this.get_active_tools(customConfigPath);
  }

  public register_job(configKey: string, jobDef: any): void {
    const list = this.jobs.get(configKey) || [];
    list.push(jobDef);
    this.jobs.set(configKey, list);
  }

  public registerJob(configKey: string, jobDef: any): void {
    this.register_job(configKey, jobDef);
  }

  public get_active_jobs(customConfigPath?: string): any[] {
    const active: any[] = [];
    for (const [configKey, jobList] of this.jobs.entries()) {
      const enabledKey = configKey.endsWith(".enabled") ? configKey : `${configKey}.enabled`;
      if (config_is_enabled(enabledKey, customConfigPath)) {
        active.push(...jobList);
      }
    }
    return active;
  }

  public getActiveJobs(customConfigPath?: string): any[] {
    return this.get_active_jobs(customConfigPath);
  }

  public disabled_http_response(configKey: string): [number, { disabled: string }] {
    const key = configKey.endsWith(".enabled") ? configKey : `${configKey}.enabled`;
    return [503, { disabled: key }];
  }

  public async health_check(
    interfaceName: string,
    name?: string,
    configKey?: string,
    customConfigPath?: string
  ): Promise<HealthStatus> {
    try {
      const prov = this.get(interfaceName, name, configKey, customConfigPath);
      if (prov && typeof prov.health_check === "function") {
        const t0 = Date.now();
        const res = await prov.health_check();
        const latency = Date.now() - t0;
        return {
          status: res.status || "ok",
          latency_ms: res.latency_ms !== undefined ? res.latency_ms : latency,
          error: res.error || null,
        };
      }
      return { status: "ok", latency_ms: 0, error: null };
    } catch (err: any) {
      if (err instanceof FeatureDisabledError) {
        return { status: "disabled", latency_ms: 0, error: err.message };
      }
      return { status: "down", latency_ms: 0, error: err?.message || String(err) };
    }
  }

  public async health_check_all(
    customConfigPath?: string
  ): Promise<{ status: string; providers: Record<string, HealthStatus> }> {
    const results: Record<string, HealthStatus> = {};
    let overall = "ok";
    for (const interfaceName of this.defaults.keys()) {
      const res = await this.health_check(interfaceName, undefined, undefined, customConfigPath);
      results[interfaceName] = res;
      if (res.status === "down") {
        overall = "down";
      } else if (res.status === "degraded" && overall !== "down") {
        overall = "degraded";
      }
    }
    return { status: overall, providers: results };
  }
}

let registryInstance: ProviderRegistry | null = null;

export function get_registry(): ProviderRegistry {
  if (!registryInstance) {
    registryInstance = new ProviderRegistry();
  }
  return registryInstance;
}

export const getRegistry = get_registry;
