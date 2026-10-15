/**
 * STDP Reinforcement (Spike-Timing-Dependent Plasticity) (§4.12)
 *
 * Temporal asymmetric learning rule adjusting graph edge weights based on turn outcome.
 */

export const A_PLUS = 0.15;
export const A_MINUS = 0.12;
export const TAU_PLUS = 300.0;
export const TAU_MINUS = 600.0;
export const W_MIN = 0.05;
export const W_MAX = 1.00;
export const PRUNE_THRESHOLD = 0.08;

export interface RetrievalEvent {
  node_id: string;
  edge_id: string;
  retrieved_at: number; // epoch ms
}

export interface OutcomeEvent {
  session_id: string;
  turn_id: string;
  success: boolean;
  occurred_at: number; // epoch ms
}

export interface TurnAuditLog {
  session_id: string;
  turn_id: string;
  outcome: OutcomeEvent;
  traversed_edges: RetrievalEvent[];
}

export function clampWeight(w: number): number {
  return Math.max(W_MIN, Math.min(W_MAX, w));
}

export function applyStdpUpdate(
  retrieval: RetrievalEvent,
  outcome: OutcomeEvent,
  currentWeight: number
): number {
  const deltaSeconds = (outcome.occurred_at - retrieval.retrieved_at) / 1000.0;
  if (deltaSeconds <= 0) {
    return clampWeight(currentWeight);
  }

  let newW = currentWeight;
  if (outcome.success) {
    const deltaW = A_PLUS * Math.exp(-deltaSeconds / TAU_PLUS);
    newW = currentWeight + deltaW;
  } else {
    const deltaW = A_MINUS * Math.exp(-deltaSeconds / TAU_MINUS);
    newW = currentWeight - deltaW;
  }
  return clampWeight(newW);
}

export class STDPManager {
  private edgeWeights: Map<string, number> = new Map();
  private prunedEdges: Set<string> = new Set();
  private defaultWeight: number;

  constructor(defaultWeight: number = 0.50) {
    this.defaultWeight = defaultWeight;
  }

  public getEdgeWeight(edgeId: string): number {
    if (this.prunedEdges.has(edgeId)) return 0.0;
    return this.edgeWeights.get(edgeId) ?? this.defaultWeight;
  }

  public setEdgeWeight(edgeId: string, weight: number): number {
    const clamped = clampWeight(weight);
    this.edgeWeights.set(edgeId, clamped);
    if (clamped <= PRUNE_THRESHOLD) {
      this.prunedEdges.add(edgeId);
    } else {
      this.prunedEdges.delete(edgeId);
    }
    return clamped;
  }

  public processTurn(turnAuditLog: TurnAuditLog): Map<string, number> {
    const results = new Map<string, number>();
    for (const ret of turnAuditLog.traversed_edges) {
      const curW = this.getEdgeWeight(ret.edge_id);
      const updatedW = applyStdpUpdate(ret, turnAuditLog.outcome, curW);
      this.setEdgeWeight(ret.edge_id, updatedW);
      results.set(ret.edge_id, updatedW);
    }
    return results;
  }
}
