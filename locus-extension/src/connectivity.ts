/**
 * SPEC §29.5 lines 7613-7671: Connectivity Check Client (F-0068 / US-106).
 * Source: OpenHuman connectivity/checker.py + Locus-original.
 */

export interface ConnectivityStatus {
  online: boolean;
  latency_ms: number | null;
  endpoint?: string | null;
  error?: string;
  status?: string;
  cached?: boolean;
}

export interface ServiceTarget {
  name: string;
  health_url: string;
}

export interface ServiceCheckItem {
  healthy: boolean;
  status_code?: number | null;
  latency_ms?: number | null;
  error?: string | null;
}

export interface ServiceCheckResult {
  status?: string;
  provider?: string;
  services: Record<string, ServiceCheckItem>;
}

export interface ConnectivityGates {
  status?: string;
  online: boolean;
  skip_inner_loop_web: boolean;
  force_local_model: boolean;
  skip_vault_sync: boolean;
  skip_web_search: boolean;
  error?: string;
}

export interface ConnectivityClientConfig {
  sidecarBaseUrl?: string;
  defaultTimeout?: number;
}

/**
 * Gate evaluation rules per SPEC §29.5:
 * Used as gate before:
 * - Inner Loop proactive passes (skip if offline)
 * - Remote model API calls (fallback to local Ollama if offline)
 * - Background vault sync (skip if offline)
 * - Web search retrieval (skip, use local only)
 */
export function shouldSkipInnerLoopWeb(online: boolean): boolean {
  return !online;
}

export function shouldForceLocalModel(online: boolean): boolean {
  return !online;
}

export function shouldSkipVaultSync(online: boolean): boolean {
  return !online;
}

export function shouldSkipWebSearch(online: boolean): boolean {
  return !online;
}

export class ConnectivityClient {
  private baseUrl: string;

  constructor(config: ConnectivityClientConfig = {}) {
    this.baseUrl = config.sidecarBaseUrl || "http://127.0.0.1:8420";
  }

  /**
   * SPEC §29.5: Check internet connectivity probe endpoints.
   */
  async check(timeout?: number, forceRefresh = false): Promise<ConnectivityStatus> {
    const res = await fetch(`${this.baseUrl}/connectivity/check`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeout, force_refresh: forceRefresh }),
    });
    if (!res.ok) {
      throw new Error(`Connectivity probe failed with HTTP ${res.status}`);
    }
    return (await res.json()) as ConnectivityStatus;
  }

  /**
   * SPEC §29.5: Check specific service endpoints (Neo4j, PostgreSQL, sidecar).
   */
  async checkServices(
    services: ServiceTarget[],
    timeout?: number
  ): Promise<ServiceCheckResult> {
    const res = await fetch(`${this.baseUrl}/connectivity/services`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ services, timeout }),
    });
    if (!res.ok) {
      throw new Error(`Service connectivity check failed with HTTP ${res.status}`);
    }
    return (await res.json()) as ServiceCheckResult;
  }

  /**
   * SPEC §29.5: Evaluate operational gates (model escalation, sync, web search, inner loop).
   */
  async evaluateGates(): Promise<ConnectivityGates> {
    const res = await fetch(`${this.baseUrl}/connectivity/gates`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Connectivity gates check failed with HTTP ${res.status}`);
    }
    return (await res.json()) as ConnectivityGates;
  }

  /**
   * Diagnostic status of connectivity checker subsystem.
   */
  async getStatus(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/connectivity/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Connectivity status failed with HTTP ${res.status}`);
    }
    return (await res.json()) as Record<string, unknown>;
  }
}

