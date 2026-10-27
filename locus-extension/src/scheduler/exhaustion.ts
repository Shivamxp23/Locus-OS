/**
 * SPEC §25.10: TypeScript client for Exhaustion Predictor.
 */

export interface ExhaustionMetricsInput {
  consecutive_high_d_tasks?: number;
  sleep_deficit_hours?: number;
  stress_trend?: number;
  current_dcs?: number;
}

export interface ExhaustionPredictionResult {
  predicted_dcs_drop: number;
  predicted_dcs_24h: number;
  preemptive_survival_recommended: boolean;
  recommended_mode: string;
  message: string;
  metrics: Record<string, unknown>;
}

export interface ExhaustionClientOptions {
  sidecarUrl?: string;
}

export class ExhaustionPredictorClient {
  private readonly baseUrl: string;

  constructor(options: ExhaustionClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async predict(metrics: ExhaustionMetricsInput): Promise<{
    status: string;
    prediction: ExhaustionPredictionResult;
  }> {
    const res = await fetch(`${this.baseUrl}/exhaustion/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metrics }),
    });
    if (!res.ok) {
      throw new Error(`Failed to predict exhaustion: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    threshold: number;
    active: boolean;
  }> {
    const res = await fetch(`${this.baseUrl}/exhaustion/status`);
    if (!res.ok) {
      throw new Error(`Failed to get exhaustion predictor status: ${res.status}`);
    }
    return res.json();
  }
}
