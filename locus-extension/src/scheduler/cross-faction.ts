/**
 * SPEC §25.15: TypeScript client for Cross-Faction Efficiency (F-0116 / US-93).
 */

export interface FactionSplitResultData {
  task_id: string;
  duration: number;
  primary_faction: string;
  secondary_factions: string[];
  allocations: Record<string, number>;
  weights: Record<string, number>;
  cross_faction_enabled: boolean;
}

export interface CrossFactionAggregateResultData {
  total_duration: number;
  faction_totals: Record<string, number>;
  task_count: number;
  cross_faction_task_count: number;
  splits: FactionSplitResultData[];
}

export interface CrossFactionStatusData {
  provider: string;
  master_enabled: boolean;
  master_switch: string;
  subsystem_enabled: boolean;
  subsystem_switch: string;
}

export interface CrossFactionClientOptions {
  sidecarUrl?: string;
}

export class CrossFactionEfficiencyClient {
  private readonly baseUrl: string;

  constructor(options: CrossFactionClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async calculateSplit(
    taskId: string,
    duration: number,
    primaryFaction: string,
    secondaryFactions?: string[],
    weights?: Record<string, number>
  ): Promise<FactionSplitResultData> {
    const res = await fetch(`${this.baseUrl}/cross-faction/split`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: taskId,
        duration,
        primary_faction: primaryFaction,
        secondary_factions: secondaryFactions,
        weights,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to calculate cross-faction split: ${res.status}`);
    }
    return res.json();
  }

  async aggregateTasks(
    tasks: Array<{
      id: string;
      duration: number;
      primary_faction: string;
      secondary_factions?: string[];
      weights?: Record<string, number>;
    }>
  ): Promise<CrossFactionAggregateResultData> {
    const res = await fetch(`${this.baseUrl}/cross-faction/aggregate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks }),
    });
    if (!res.ok) {
      throw new Error(`Failed to aggregate cross-faction tasks: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<CrossFactionStatusData> {
    const res = await fetch(`${this.baseUrl}/cross-faction/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch cross-faction status: ${res.status}`);
    }
    return res.json();
  }
}
