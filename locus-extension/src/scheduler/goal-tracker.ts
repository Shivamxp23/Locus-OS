/**
 * SPEC §25.12: TypeScript client for Goal Tracker (3-Layer Stack) and Faction Balancer.
 */

export interface GoalTrackerValidationResult {
  status: string;
  task_id: string;
  valid: boolean;
  message: string;
}

export interface FactionBalanceReportData {
  total_minutes: number;
  allocations_minutes: Record<string, number>;
  actual_fractions: Record<string, number>;
  target_fractions: Record<string, number>;
  under_represented: string[];
  over_represented: string[];
  compliant: boolean;
}

export interface AssignmentCheckResult {
  status: string;
  allowed: boolean;
  message: string;
  candidate_faction: string;
  proposed_minutes: number;
}

export interface GoalTrackerClientOptions {
  sidecarUrl?: string;
}

export class GoalTrackerClient {
  private readonly baseUrl: string;

  constructor(options: GoalTrackerClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async validateHierarchy(taskId: string): Promise<GoalTrackerValidationResult> {
    const res = await fetch(`${this.baseUrl}/goal-tracker/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: taskId }),
    });
    if (!res.ok) {
      throw new Error(`Failed to validate hierarchy: ${res.status}`);
    }
    return res.json();
  }

  async detectOrphans(): Promise<{
    status: string;
    count: number;
    orphans: Array<Record<string, unknown>>;
  }> {
    const res = await fetch(`${this.baseUrl}/goal-tracker/orphans`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to detect orphans: ${res.status}`);
    }
    return res.json();
  }

  async evaluateFactionBalance(
    allocationsMinutes: Record<string, number>
  ): Promise<{
    status: string;
    balance_report: FactionBalanceReportData;
  }> {
    const res = await fetch(`${this.baseUrl}/goal-tracker/balance-check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allocations_minutes: allocationsMinutes }),
    });
    if (!res.ok) {
      throw new Error(`Failed to evaluate balance: ${res.status}`);
    }
    return res.json();
  }

  async checkAssignmentAllowed(
    candidateFaction: string,
    proposedMinutes: number,
    currentAllocations: Record<string, number>,
    waitingFactions: string[]
  ): Promise<AssignmentCheckResult> {
    const res = await fetch(`${this.baseUrl}/goal-tracker/assignment-allowed`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        candidate_faction: candidateFaction,
        proposed_minutes: proposedMinutes,
        current_allocations: currentAllocations,
        waiting_factions: waitingFactions,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to check assignment: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    enabled: boolean;
    total_nodes: number;
    targets: Record<string, number>;
    tolerance: number;
  }> {
    const res = await fetch(`${this.baseUrl}/goal-tracker/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get status: ${res.status}`);
    }
    return res.json();
  }
}
