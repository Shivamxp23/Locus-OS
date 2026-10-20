/**
 * locus-extension/src/memory/spaced-repetition.ts
 *
 * SPEC §4.13: TypeScript client for Spaced Repetition Memory Consolidation (FSRS / SM-2).
 * Interfaces with Python sidecar for evaluating memory retention intervals, ease factors,
 * due date tracking, and core fact promotions.
 */

export interface MemoryNodeState {
  node_id: string;
  repetition_count: number;
  ease_factor: number;
  interval_days: number;
  stability: number;
  last_reviewed_at: number;
  due_date: number;
  lapses: number;
  is_core_fact: boolean;
  metadata?: Record<string, unknown>;
}

export interface SpacedRepetitionConfig {
  enabled: boolean;
  default_ease_factor: number;
  min_ease_factor: number;
  initial_interval_first: number;
  initial_interval_second: number;
  core_fact_min_repetitions: number;
  core_fact_min_ease: number;
  max_batch_size: number;
  storage_path?: string | null;
}

export interface ConsolidatedNode {
  node_id: string;
  grade: number;
  interval_days: number;
  ease_factor: number;
  repetition_count: number;
  is_core_fact: boolean;
  due_date: number;
}

export interface ConsolidationResult {
  processed_count: number;
  promoted_core_facts: string[];
  nodes: ConsolidatedNode[];
  timestamp: number;
}

export const DEFAULT_EASE_FACTOR = 2.50;
export const MIN_EASE_FACTOR = 1.30;
export const SECONDS_PER_DAY = 86400;

/**
 * Local offline evaluation of SM-2 algorithm per SPEC §4.13 lines 1354-1379.
 */
export function calculateLocalNextReview(
  state: MemoryNodeState,
  qualityGrade: number,
  nowTimestamp?: number
): MemoryNodeState {
  const grade = Math.max(0, Math.min(5, Math.floor(qualityGrade)));
  const now = nowTimestamp ?? Date.now() / 1000;

  let repCount = state.repetition_count;
  let interval = state.interval_days;
  let ease = state.ease_factor;
  let stability = state.stability;
  let lapses = state.lapses;

  if (grade >= 3) {
    if (repCount === 0) {
      interval = 1;
    } else if (repCount === 1) {
      interval = 6;
    } else {
      interval = Math.max(1, Math.round(interval * ease));
    }
    repCount += 1;
    stability = Number((stability * (1.0 + 0.19 * (grade - 2.0) * (ease / DEFAULT_EASE_FACTOR))).toFixed(4));
  } else {
    repCount = 0;
    interval = 1;
    lapses += 1;
    stability = Math.max(0.20, Number((stability * 0.50).toFixed(4)));
  }

  const diff = 5 - grade;
  const deltaEase = 0.1 - diff * (0.08 + diff * 0.02);
  ease = Math.max(MIN_EASE_FACTOR, Number((ease + deltaEase).toFixed(4)));

  const isCoreFact = repCount >= 5 && ease >= 2.50;

  return {
    node_id: state.node_id,
    repetition_count: repCount,
    ease_factor: ease,
    interval_days: interval,
    stability,
    last_reviewed_at: now,
    due_date: now + interval * SECONDS_PER_DAY,
    lapses,
    is_core_fact: isCoreFact,
    metadata: state.metadata ? { ...state.metadata } : {},
  };
}

export class SpacedRepetitionClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async getConfig(): Promise<SpacedRepetitionConfig> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/config`);
    if (!res.ok) {
      throw new Error(`Failed to fetch Spaced Repetition config: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<SpacedRepetitionConfig>;
  }

  async calculateNextReview(state: MemoryNodeState, qualityGrade: number): Promise<MemoryNodeState> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state, quality_grade: qualityGrade }),
    });
    if (!res.ok) {
      throw new Error(`Failed to calculate next review: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<MemoryNodeState>;
  }

  async recordReview(nodeId: string, qualityGrade: number, timestamp?: number): Promise<MemoryNodeState> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: nodeId,
        quality_grade: qualityGrade,
        timestamp,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to record review for ${nodeId}: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<MemoryNodeState>;
  }

  async getDueNodes(limit: number = 50, timestamp?: number): Promise<MemoryNodeState[]> {
    const url = new URL(`${this.baseUrl}/memory/spaced_repetition/due`);
    url.searchParams.set("limit", limit.toString());
    if (timestamp !== undefined) {
      url.searchParams.set("timestamp", timestamp.toString());
    }
    const res = await fetch(url.toString());
    if (!res.ok) {
      throw new Error(`Failed to fetch due nodes: ${res.status} ${res.statusText}`);
    }
    const data = await res.json() as { nodes: MemoryNodeState[] };
    return data.nodes;
  }

  async runConsolidation(
    limit: number = 50,
    simulatedGrades?: Record<string, number>,
    timestamp?: number
  ): Promise<ConsolidationResult> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/consolidate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        limit,
        simulated_grades: simulatedGrades,
        timestamp,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to run consolidation: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<ConsolidationResult>;
  }

  async getNodeState(nodeId: string): Promise<MemoryNodeState> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/nodes/${encodeURIComponent(nodeId)}`);
    if (!res.ok) {
      throw new Error(`Failed to get node state for ${nodeId}: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<MemoryNodeState>;
  }

  async saveNodeState(nodeId: string, state: Partial<MemoryNodeState>): Promise<{ status: string; node: MemoryNodeState }> {
    const res = await fetch(`${this.baseUrl}/memory/spaced_repetition/nodes/${encodeURIComponent(nodeId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    if (!res.ok) {
      throw new Error(`Failed to save node state for ${nodeId}: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<{ status: string; node: MemoryNodeState }>;
  }
}

// Alias for client
export const SpacedRepetitionAdapter = SpacedRepetitionClient;
