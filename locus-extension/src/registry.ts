/**
 * SPEC §03 / F-0125: Universal Provider Registry in TypeScript.
 */

export class ProviderRegistry {
  private providers: Map<string, Map<string, any>> = new Map();
  private instances: Map<string, any> = new Map();

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
