/**
 * SPEC §25.11: TypeScript client for Weekly Faction Rebalance.
 */

export interface RebalanceRequest {
  actual_hours?: Record<string, number>;
  base_weights?: Record<string, number>;
  target_percentages?: Record<string, number>;
  correction_factor?: number;
}

export interface RebalanceResultData {
  actual_hours: Record<string, number>;
  total_hours: number;
  actual_percentages: Record<string, number>;
  target_percentages: Record<string, number>;
  deficits: Record<string, number>;
  base_weights: Record<string, number>;
  adjusted_weights: Record<string, number>;
  normalized_weights: Record<string, number>;
  correction_factor: number;
  rebalance_time: string;
}

export interface RebalanceClientOptions {
  sidecarUrl?: string;
}

export class WeeklyFactionRebalanceClient {
  private readonly baseUrl: string;

  constructor(options: RebalanceClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async calculateRebalance(request: RebalanceRequest = {}): Promise<{
    status: string;
    rebalance: RebalanceResultData;
  }> {
    const res = await fetch(`${this.baseUrl}/rebalance/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      throw new Error(`Failed to calculate rebalance: ${res.status}`);
    }
    return res.json();
  }

  async getActiveWeights(): Promise<{
    status: string;
    weights: Record<string, number>;
  }> {
    const res = await fetch(`${this.baseUrl}/rebalance/weights`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get active weights: ${res.status}`);
    }
    return res.json();
  }

  async recordDuration(
    faction: string,
    durationHours: number
  ): Promise<{
    status: string;
    durations: Record<string, number>;
  }> {
    const res = await fetch(`${this.baseUrl}/rebalance/duration`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        faction,
        duration_hours: durationHours,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to record duration: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    enabled: boolean;
    active_weights: Record<string, number>;
    logged_durations: Record<string, number>;
    default_targets: Record<string, number>;
  }> {
    const res = await fetch(`${this.baseUrl}/rebalance/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get rebalance status: ${res.status}`);
    }
    return res.json();
  }
}
