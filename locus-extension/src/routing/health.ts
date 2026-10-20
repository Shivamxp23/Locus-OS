/**
 * SPEC §2.7-2.8 / F-0096 / US-37: Local Health Checker (health.rs).
 * Provides cached probe with 30-second TTL and 3-second timeout.
 * Lock / concurrency discipline: reads cache first, then probes if expired.
 */

import { HealthStatus, RoutingConfig, DEFAULT_ROUTING_CONFIG } from "./types";

export class LocalHealthChecker {
  private cachedStatus: HealthStatus | null = null;
  private config: RoutingConfig;

  constructor(config: Partial<RoutingConfig> = {}) {
    this.config = { ...DEFAULT_ROUTING_CONFIG, ...config };
  }

  /**
   * Retrieves health status of local model endpoint.
   * Returns cached status if fresh (< 30s TTL).
   */
  async checkHealth(forceRefresh = false): Promise<HealthStatus> {
    const now = Date.now();
    if (!forceRefresh && this.cachedStatus !== null) {
      if (now - this.cachedStatus.lastCheck < this.config.healthCacheTtlMs) {
        return this.cachedStatus;
      }
    }

    const endpoint =
      this.config.localProvider === "ollama"
        ? `${this.config.localBaseUrl}/api/tags`
        : `${this.config.localBaseUrl}/models`;

    let healthy = false;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      const res = await fetch(endpoint, {
        method: "GET",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        healthy = true;
      }
    } catch {
      healthy = false;
    }

    this.cachedStatus = {
      healthy,
      lastCheck: Date.now(),
      endpoint,
      providerType: this.config.localProvider,
    };

    return this.cachedStatus;
  }

  /**
   * Test injection helper to set cached status.
   */
  setCachedHealth(healthy: boolean): void {
    this.cachedStatus = {
      healthy,
      lastCheck: Date.now(),
      endpoint: this.config.localBaseUrl,
      providerType: this.config.localProvider,
    };
  }

  clearCache(): void {
    this.cachedStatus = null;
  }
}
