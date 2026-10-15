/**
 * locus-extension/src/providers/memory/interface.ts - Memory Provider Interface
 *
 * Implements Spec §4.18 (Memory Provider Interface).
 */

export type EntityType = "Person" | "Object" | "Location" | "Event" | "Organization" | "Preference" | "Fact";

export interface MemoryEntry {
  id: string;
  name: string;
  entityType: EntityType;
  properties?: Record<string, unknown>;
  weight?: number;
  createdAt?: number;
}

export interface Pathway {
  sourceName: string;
  relation: string;
  targetName: string;
  weight: number;
}

export interface MemoryProvider {
  addEntity(name: string, entityType: EntityType, properties?: Record<string, unknown>): Promise<MemoryEntry>;
  writeRelation(sourceName: string, relation: string, targetName: string, weight?: number): Promise<Pathway>;
  getContext(query: string, maxTokens?: number): Promise<string>;
}
