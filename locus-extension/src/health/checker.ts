/**
 * SPEC §29.3 lines 7501-7530: Health Checks Client (F-0066 / US-104).
 * Source: Hermes gateway/status.py + OpenHuman health.
 */

export interface ProviderHealthResult {
  status: "ok" | "error" | "disabled";
  latency_ms: number;
  details?: unknown;
  error?: string;
}

export interface HealthCheckAllResponse {
  status: "ok" | "error";
  results: Record<string, ProviderHealthResult>;
  count: number;
}

export interface SystemHealthReport {
  overall_status: "ok" | "degraded" | "error";
  timestamp: number;
  total_providers: number;
  healthy_providers: number;
  failing_providers: number;
  results: Record<string, ProviderHealthResult>;
}

export interface HealthCheckerConfig {
  sidecarBaseUrl?: string;
}

export class HealthCheckerClient {
  private baseUrl: string;

  constructor(config: HealthCheckerConfig = {}) {
    this.baseUrl = config.sidecarBaseUrl || "http://127.0.0.1:8420";
  }

  /**
   * SPEC §29.3: Run health checks across all registered providers via sidecar diagnostics.
   */
  async healthCheckAll(): Promise<HealthCheckAllResponse> {
    const res = await fetch(`${this.baseUrl}/diagnostics/health/all`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Health check request failed with HTTP ${res.status}`);
    }
    return (await res.json()) as HealthCheckAllResponse;
  }

  /**
   * Get comprehensive aggregate system health report.
   */
  async getReport(): Promise<SystemHealthReport> {
    const res = await fetch(`${this.baseUrl}/diagnostics/health/report`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Health report request failed with HTTP ${res.status}`);
    }
    return (await res.json()) as SystemHealthReport;
  }

  /**
   * Query status of health checks subsystem.
   */
  async getStatus(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/diagnostics/health/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Health status request failed with HTTP ${res.status}`);
    }
    return (await res.json()) as Record<string, unknown>;
  }
}
