/**
 * SPEC §03 / F-0125 / US-06: Universal Provider Registry in TypeScript.
 * Enforces modular register, get, active provider resolution by config,
 * and off-switch behavior for tools and routes.
 */
import { get as getConfig, isEnabled } from "./config.ts";

export class ProviderRegistry {
  private providers: Map<string, Map<string, any>> = new Map();
  private instances: Map<string, any> = new Map();
  private tools: Map<string, any> = new Map();

  register(area: string, name: string, provider: any): void {
    if (!this.providers.has(area)) {
      this.providers.set(area, new Map());
    }
    this.providers.get(area)!.set(name, provider);
  }

  get(area: string, name?: string): any {
    const areaMap = this.providers.get(area);
    if (!areaMap) return null;
    if (name) return areaMap.get(name) || null;
    return areaMap.values().next().value || null;
  }

  getActiveProvider(area: string, feature?: string, defaultName?: string): any {
    let chosen: string | null = null;
    if (feature) {
      chosen = getConfig(`locus.${area}.${feature}.provider`);
    }
    if (!chosen) {
      chosen = getConfig(`locus.${area}.provider`);
    }
    if (!chosen) {
      chosen = defaultName || null;
    }
    return this.get(area, chosen || undefined);
  }

  /**
   * Register a tool only if its feature switch is enabled.
   * If configKey evaluates to false, tool is NOT registered.
   */
  registerTool(toolName: string, configKey: string, toolDef: any): boolean {
    if (!isEnabled(configKey)) {
      return false;
    }
    this.tools.set(toolName, toolDef);
    return true;
  }

  getRegisteredTools(): string[] {
    return Array.from(this.tools.keys());
  }

  /**
   * Check if an HTTP route is allowed.
   * Returns 503 with {"disabled": configKey} if disabled, null if allowed.
   */
  checkRouteAllowed(configKey: string): { status: number; body: { disabled: string } } | null {
    if (!isEnabled(configKey)) {
      return { status: 503, body: { disabled: configKey } };
    }
    return null;
  }

  listProviders(area?: string): string[] {
    if (area) {
      const areaMap = this.providers.get(area);
      return areaMap ? Array.from(areaMap.keys()) : [];
    }
    const out: string[] = [];
    for (const [a, pmap] of this.providers.entries()) {
      for (const name of pmap.keys()) {
        out.push(`${a}.${name}`);
      }
    }
    return out;
  }
}

let globalRegistry: ProviderRegistry | null = null;

export function getRegistry(): ProviderRegistry {
  if (!globalRegistry) {
    globalRegistry = new ProviderRegistry();
  }
  return globalRegistry;
}
