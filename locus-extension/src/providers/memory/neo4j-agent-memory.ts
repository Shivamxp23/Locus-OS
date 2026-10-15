/**
 * locus-extension/src/providers/memory/neo4j-agent-memory.ts
 *
 * Implements Spec §4.1-4.2 (Neo4j Agent Memory POLE+O Client).
 */

import { EntityType, MemoryEntry, MemoryProvider, Pathway } from "./interface.js";

export class RemoteNeo4jMemoryProvider implements MemoryProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/memory";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async addEntity(
    name: string,
    entityType: EntityType,
    properties?: Record<string, unknown>
  ): Promise<MemoryEntry> {
    if (!this.enabled) {
      return { id: "disabled", name, entityType };
    }
    try {
      const res = await fetch(`${this.endpoint}/entity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, entity_type: entityType, properties }),
      });
      return (await res.json()) as MemoryEntry;
    } catch {
      return { id: `local-${Date.now()}`, name, entityType, properties };
    }
  }

  public async writeRelation(
    sourceName: string,
    relation: string,
    targetName: string,
    weight: number = 0.5
  ): Promise<Pathway> {
    if (!this.enabled) {
      return { sourceName, relation, targetName, weight: 0.0 };
    }
    try {
      const res = await fetch(`${this.endpoint}/relation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: sourceName, relation, target_name: targetName, weight }),
      });
      return (await res.json()) as Pathway;
    } catch {
      return { sourceName, relation, targetName, weight };
    }
  }

  public async getContext(query: string, maxTokens: number = 150): Promise<string> {
    if (!this.enabled) return "";
    try {
      const res = await fetch(
        `${this.endpoint}/context?query=${encodeURIComponent(query)}&max_tokens=${maxTokens}`
      );
      if (!res.ok) return "";
      const data = (await res.json()) as { context: string };
      return data.context ?? "";
    } catch {
      return "";
    }
  }
}
