/**
 * locus-extension/src/trajectory.ts - Pi Agent Trajectory Telemetry Extension
 *
 * Implements Spec §19.2 (Trajectory Recording).
 * Intercepts turns, formats telemetry records, and interfaces with the trajectory storage.
 */

export interface TrajectoryTurnRecord {
  sessionId: string;
  turnId: string;
  timestamp: number;
  prompt: string;
  response: string;
  toolCalls: Array<{ name: string; parameters?: Record<string, unknown>; result?: unknown }>;
  tokens: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  durationMs: number;
  metadata?: Record<string, unknown>;
}

export class TrajectoryManager {
  private enabled: boolean;
  private endpoint: string;

  constructor(options: { enabled?: boolean; endpoint?: string } = {}) {
    this.enabled = options.enabled ?? true;
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/trajectory";
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public formatTurn(turn: TrajectoryTurnRecord): TrajectoryTurnRecord {
    return {
      sessionId: turn.sessionId,
      turnId: turn.turnId || `turn-${Date.now()}`,
      timestamp: turn.timestamp || Date.now(),
      prompt: turn.prompt,
      response: turn.response,
      toolCalls: turn.toolCalls || [],
      tokens: turn.tokens || { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
      durationMs: turn.durationMs || 0,
      metadata: turn.metadata || {},
    };
  }

  public async recordTurn(turn: TrajectoryTurnRecord): Promise<boolean> {
    if (!this.enabled) {
      return false;
    }
    const record = this.formatTurn(turn);
    try {
      const res = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(record),
      });
      return res.ok;
    } catch {
      // In standalone or offline mode, fail gracefully
      return false;
    }
  }
}
