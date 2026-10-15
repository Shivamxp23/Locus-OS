/**
 * locus-extension/src/health.ts - Health Monitor TypeScript client.
 *
 * Implements Spec §29.3
 */

export interface ComponentStatus {
  status: "healthy" | "degraded" | "unhealthy";
  latencyMs: number;
}

export class HealthClient {
  public isHealthy(status: ComponentStatus): boolean {
    return status.status === "healthy";
  }
}
