/**
 * SPEC §25.16: TypeScript client for Four-Level Emergency Protocol (F-0117 / US-94).
 */

export enum EmergencyLevel {
  LEVEL_0_NORMAL = 0,
  LEVEL_1_MINOR = 1,
  LEVEL_2_MODERATE = 2,
  LEVEL_3_MAJOR = 3,
  LEVEL_4_CRISIS = 4,
}

export interface EmergencyAssessmentData {
  level: number;
  level_name: string;
  description: string;
  mode_override: string;
  recommended_action: string;
  redistribution_window_days: number;
  affected_factions: Record<string, string>;
  tool_permissions: Record<string, boolean>;
  overrides_applied: boolean;
  enabled: boolean;
}

export interface ProtocolActivationResultData {
  success: boolean;
  level: number;
  level_name: string;
  mode_override: string;
  message: string;
  redistribution_window_days: number;
  tool_permissions: Record<string, boolean>;
  affected_factions: Record<string, string>;
  overrides_applied: boolean;
}

export interface ProtocolDeactivationResultData {
  success: boolean;
  previous_level: number;
  message: string;
  require_weekly_review: boolean;
  redistribution_window_days: number;
}

export interface EmergencyProtocolStatusData {
  current_level: number;
  current_level_name: string;
  is_emergency_active: boolean;
  mode_override: string;
  enabled: boolean;
  redistribution_window_days: number;
  tool_permissions: Record<string, boolean>;
  crisis_hierarchy: string[];
  history: Array<Record<string, unknown>>;
  feature_enabled?: boolean;
  subsystem_enabled?: boolean;
}

export interface EmergencyProtocolClientOptions {
  sidecarUrl?: string;
}

export class EmergencyProtocolClient {
  private readonly baseUrl: string;

  constructor(options: EmergencyProtocolClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async evaluate(params: {
    disruption_hours?: number;
    disruption_days?: number;
    is_life_event?: boolean;
    trigger_reason?: string;
  }): Promise<EmergencyAssessmentData> {
    const res = await fetch(`${this.baseUrl}/emergency-protocol/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    if (!res.ok) {
      throw new Error(`Failed to evaluate emergency situation: ${res.status}`);
    }
    return res.json();
  }

  async activate(level: number, reason?: string): Promise<ProtocolActivationResultData> {
    const res = await fetch(`${this.baseUrl}/emergency-protocol/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, reason: reason || "" }),
    });
    if (!res.ok) {
      throw new Error(`Failed to activate emergency protocol: ${res.status}`);
    }
    return res.json();
  }

  async deactivate(): Promise<ProtocolDeactivationResultData> {
    const res = await fetch(`${this.baseUrl}/emergency-protocol/deactivate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) {
      throw new Error(`Failed to deactivate emergency protocol: ${res.status}`);
    }
    return res.json();
  }

  async applyOverrides(
    tasks: Array<Record<string, unknown>>,
    level?: number
  ): Promise<{
    tasks_retained: Array<Record<string, unknown>>;
    tasks_deferred: Array<Record<string, unknown>>;
    tasks_suspended: Array<Record<string, unknown>>;
    mode: string;
    overrides_applied: boolean;
    level: number;
    redistribution_window_days?: number;
  }> {
    const res = await fetch(`${this.baseUrl}/emergency-protocol/apply-overrides`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tasks, level }),
    });
    if (!res.ok) {
      throw new Error(`Failed to apply emergency scheduling overrides: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<EmergencyProtocolStatusData> {
    const res = await fetch(`${this.baseUrl}/emergency-protocol/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch emergency protocol status: ${res.status}`);
    }
    return res.json();
  }
}
