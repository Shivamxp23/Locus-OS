/**
 * Spaced Repetition Memory Consolidation (SM-2 / FSRS) (§4.13)
 *
 * Computes memory node review intervals and handles nightly consolidation queues.
 */

export const MIN_EASE_FACTOR = 1.30;
export const DEFAULT_EASE_FACTOR = 2.50;

export interface MemoryNodeState {
  node_id: string;
  repetition_count: number;
  ease_factor: number;
  interval_days: number;
  stability: number;
  last_reviewed_at?: string;
  due_date?: string;
}

export function calculateNextReview(
  state: MemoryNodeState,
  qualityGrade: number,
  currentTime?: Date
): MemoryNodeState {
  const now = currentTime || new Date();
  const grade = Math.max(0, Math.min(5, qualityGrade));

  if (grade >= 3) {
    if (state.repetition_count === 0) {
      state.interval_days = 1;
    } else if (state.repetition_count === 1) {
      state.interval_days = 6;
    } else {
      state.interval_days = Math.max(1, Math.round(state.interval_days * state.ease_factor));
    }
    state.repetition_count += 1;
  } else {
    state.repetition_count = 0;
    state.interval_days = 1;
  }

  const deltaEf = 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02);
  state.ease_factor = Math.max(MIN_EASE_FACTOR, state.ease_factor + deltaEf);

  if (grade >= 3) {
    state.stability = Math.round(state.stability * (1.0 + (grade - 2) * 0.2) * 1000) / 1000;
  } else {
    state.stability = Math.max(0.5, Math.round(state.stability * 0.6 * 1000) / 1000);
  }

  state.last_reviewed_at = now.toISOString();
  const nextDate = new Date(now.getTime() + state.interval_days * 24 * 60 * 60 * 1000);
  state.due_date = nextDate.toISOString();
  return state;
}

export class MemoryScheduler {
  private nodeStates: Map<string, MemoryNodeState> = new Map();

  public registerNode(nodeId: string, easeFactor: number = DEFAULT_EASE_FACTOR): MemoryNodeState {
    const now = new Date();
    const state: MemoryNodeState = {
      node_id: nodeId,
      repetition_count: 0,
      ease_factor: easeFactor,
      interval_days: 1,
      stability: 1.0,
      due_date: now.toISOString(),
    };
    this.nodeStates.set(nodeId, state);
    return state;
  }

  public recordReview(nodeId: string, grade: number): MemoryNodeState {
    let state = this.nodeStates.get(nodeId);
    if (!state) {
      state = this.registerNode(nodeId);
    }
    const updated = calculateNextReview(state, grade);
    this.nodeStates.set(nodeId, updated);
    return updated;
  }

  public getDueNodes(asOf?: Date): MemoryNodeState[] {
    const targetIso = (asOf || new Date()).toISOString();
    const dueList: MemoryNodeState[] = [];
    for (const state of this.nodeStates.values()) {
      if (!state.due_date || state.due_date <= targetIso) {
        dueList.push(state);
      }
    }
    return dueList.sort((a, b) => (a.due_date || "").localeCompare(b.due_date || ""));
  }
}
