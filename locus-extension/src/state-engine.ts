/**
 * SPEC §2.4 / F-0093 / US-33: TypeScript State Engine (Stage 3).
 * Tracks Daily Capacity Score (DCS), Operating Modes (SURVIVAL -> PEAK),
 * and maintains CURRENT_STATE snapshot for Context Forge and Inner Loop.
 */
import { isEnabled } from "./config";

export type OperatingMode =
  | "SURVIVAL"
  | "RECOVERY"
  | "NORMAL"
  | "DEEP_WORK"
  | "PEAK";

export interface CheckInInput {
  energy: number; // 1-10
  mood: number; // 1-10
  sleep: number; // 1-10
  stress: number; // 0-10
  timestamp?: number;
}

export interface CurrentState {
  dcs: number;
  operating_mode: OperatingMode;
  energy: number;
  mood: number;
  sleep: number;
  stress: number;
  active_alerts: string[];
  inferred_cause_chain?: string | null;
  updated_at: number;
}

export class StateEngine {
  private sidecarBaseUrl: string;

  constructor(sidecarBaseUrl: string = "http://127.0.0.1:8420") {
    this.sidecarBaseUrl = sidecarBaseUrl;
  }

  public isFeatureEnabled(): boolean {
    return isEnabled("locus.state_engine.enabled");
  }

  /**
   * SPEC §2.4 STEP 3: Canonical DCS Calculation
   * Formula: DCS = ((E + M + S) / 3) * (1 - ST / 20)
   */
  public calculateDCS(
    energy: number,
    mood: number,
    sleep: number,
    stress: number
  ): number {
    const e = Math.max(1, Math.min(10, energy));
    const m = Math.max(1, Math.min(10, mood));
    const s = Math.max(1, Math.min(10, sleep));
    const inputStress = Math.max(0, Math.min(10, stress));
    const st = inputStress * 2.0;

    const baseAvg = (e + m + s) / 3.0;
    const stressFactor = Math.max(0, 1.0 - st / 20.0);
    const dcs = baseAvg * stressFactor;

    return Math.round(Math.max(0, Math.min(10, dcs)) * 100) / 100;
  }

  /**
   * SPEC §2.4 STEP 4: Operating Mode Determination
   */
  public determineOperatingMode(dcs: number): OperatingMode {
    if (dcs <= 2.0) return "SURVIVAL";
    if (dcs <= 4.0) return "RECOVERY";
    if (dcs <= 6.0) return "NORMAL";
    if (dcs <= 8.0) return "DEEP_WORK";
    return "PEAK";
  }

  /**
   * Fetch current state snapshot from sidecar.
   */
  public async getCurrentState(): Promise<CurrentState> {
    if (!this.isFeatureEnabled()) {
      return {
        dcs: 5.0,
        operating_mode: "NORMAL",
        energy: 5.0,
        mood: 5.0,
        sleep: 5.0,
        stress: 2.5,
        active_alerts: [],
        updated_at: Date.now() / 1000,
      };
    }

    try {
      const response = await fetch(`${this.sidecarBaseUrl}/state/current`);
      if (response.ok) {
        const data = (await response.json()) as { state: CurrentState };
        return data.state;
      }
    } catch {
      // Fallback on network failure
    }

    const dcs = this.calculateDCS(5.0, 5.0, 5.0, 2.5);
    return {
      dcs,
      operating_mode: this.determineOperatingMode(dcs),
      energy: 5.0,
      mood: 5.0,
      sleep: 5.0,
      stress: 2.5,
      active_alerts: [],
      updated_at: Date.now() / 1000,
    };
  }

  /**
   * Submit check-in update to sidecar.
   */
  public async submitCheckin(checkin: CheckInInput): Promise<CurrentState> {
    if (!this.isFeatureEnabled()) {
      const dcs = this.calculateDCS(checkin.energy, checkin.mood, checkin.sleep, checkin.stress);
      return {
        dcs,
        operating_mode: this.determineOperatingMode(dcs),
        energy: checkin.energy,
        mood: checkin.mood,
        sleep: checkin.sleep,
        stress: checkin.stress,
        active_alerts: [],
        updated_at: Date.now() / 1000,
      };
    }

    const response = await fetch(`${this.sidecarBaseUrl}/state/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(checkin),
    });

    if (!response.ok) {
      throw new Error(`State engine check-in failed with status ${response.status}`);
    }

    const data = (await response.json()) as { state: CurrentState };
    return data.state;
  }
}
