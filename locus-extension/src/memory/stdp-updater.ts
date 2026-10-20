/**
 * locus-extension/src/memory/stdp-updater.ts
 *
 * SPEC §4.12: TypeScript client for STDP Reinforcement (Spike-Timing-Dependent Plasticity).
 * Interfaces with Python sidecar for applying asymmetric temporal edge weight updates,
 * batch turn reinforcement, and low-weight relationship pruning.
 */

export interface RetrievalEvent {
  node_id: string;
  edge_id: string;
  retrieved_at: number; // epoch timestamp
}

export interface OutcomeEvent {
  session_id: string;
  turn_id: string;
  success: boolean;
  occurred_at: number;
}

export interface TraversedEdgeRecord {
  edge_id: string;
  retrieval_event: RetrievalEvent;
  initial_weight?: number | null;
}

export interface TurnAuditLog {
  session_id: string;
  turn_id: string;
  traversed_edges: TraversedEdgeRecord[];
  outcome?: OutcomeEvent | null;
}

export interface STDPConfig {
  enabled: boolean;
  a_plus: number;
  a_minus: number;
  tau_plus: number;
  tau_minus: number;
  w_min: number;
  w_max: number;
  prune_threshold: number;
  storage_path?: string | null;
}

export interface EdgeUpdateResult {
  edge_id: string;
  node_id: string;
  old_weight: number;
  new_weight: number;
  delta_t: number;
  success: boolean;
  pruned: boolean;
}

export interface TurnSTDPResult {
  session_id: string;
  turn_id: string;
  updated_edges: EdgeUpdateResult[];
  pruned_tags: string[];
}

export interface PruneCandidate {
  edge_id: string;
  reason: string;
  weight: number;
  tagged_at: number;
}

export class STDPClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async getConfig(): Promise<STDPConfig> {
    const res = await fetch(`${this.baseUrl}/memory/stdp/config`);
    if (!res.ok) {
      throw new Error(`Failed to fetch STDP config: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.config as STDPConfig;
  }

  async applyUpdate(
    retrieval: RetrievalEvent,
    outcome: OutcomeEvent,
    currentWeight: number
  ): Promise<number> {
    const res = await fetch(`${this.baseUrl}/memory/stdp/update`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        retrieval,
        outcome,
        current_weight: currentWeight,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to calculate STDP update: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.updated_weight as number;
  }

  async processTurn(turnAuditLog: TurnAuditLog): Promise<TurnSTDPResult> {
    const res = await fetch(`${this.baseUrl}/memory/stdp/process_turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(turnAuditLog),
    });
    if (!res.ok) {
      throw new Error(`Failed to process turn STDP: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.result as TurnSTDPResult;
  }

  async getEdgeWeight(edgeId: string): Promise<number> {
    const res = await fetch(
      `${this.baseUrl}/memory/stdp/weights/${encodeURIComponent(edgeId)}`
    );
    if (!res.ok) {
      throw new Error(`Failed to get edge weight: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.weight as number;
  }

  async setEdgeWeight(edgeId: string, weight: number): Promise<number> {
    const res = await fetch(
      `${this.baseUrl}/memory/stdp/weights/${encodeURIComponent(edgeId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weight }),
      }
    );
    if (!res.ok) {
      throw new Error(`Failed to set edge weight: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.weight as number;
  }

  async listPruneCandidates(): Promise<PruneCandidate[]> {
    const res = await fetch(`${this.baseUrl}/memory/stdp/prune_candidates`);
    if (!res.ok) {
      throw new Error(`Failed to list prune candidates: ${res.status} ${res.statusText}`);
    }
    const data = await res.json();
    return data.candidates as PruneCandidate[];
  }
}
