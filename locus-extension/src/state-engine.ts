/**
 * locus-extension/src/state-engine.ts - State Engine Client
 *
 * Implements Spec §2.4 (State Engine Stage 3).
 */

export type OperatingMode = "SURVIVAL" | "RECOVERY" | "NORMAL" | "DEEP_WORK" | "PEAK";

export interface CurrentState {
  dcs: number;
  operating_mode: OperatingMode;
  energy: number;
  mood: number;
  stress: number;
  sleep: number;
  active_alerts: string[];
  inferred_cause_chain: string;
  last_updated: number;
}

export interface StateEngineProvider {
  getState(): Promise<CurrentState>;
}

export class RemoteStateEngine implements StateEngineProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/state";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async getState(): Promise<CurrentState> {
    if (!this.enabled) {
      return {
        dcs: 5.0,
        operating_mode: "NORMAL",
        energy: 5.0,
        mood: 5.0,
        stress: 5.0,
        sleep: 5.0,
        active_alerts: ["STATE_ENGINE_DISABLED"],
        inferred_cause_chain: "State engine disabled by configuration.",
        last_updated: Date.now() / 1000,
      };
    }

    try {
      const res = await fetch(this.endpoint);
      if (!res.ok) throw new Error(`State engine HTTP ${res.status}`);
      return (await res.json()) as CurrentState;
    } catch {
      // Safe baseline fallback
      return {
        dcs: 5.0,
        operating_mode: "NORMAL",
        energy: 5.0,
        mood: 5.0,
        stress: 5.0,
        sleep: 5.0,
        active_alerts: ["OFFLINE_FALLBACK"],
        inferred_cause_chain: "Using offline baseline state.",
        last_updated: Date.now() / 1000,
      };
    }
  }
}
