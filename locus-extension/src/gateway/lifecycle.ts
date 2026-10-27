/**
 * SPEC §17.10 lines 3855-3926:
 * Graceful Gateway Restart & State Snapshotting TypeScript Client Contract (F-0047 / US-80).
 *
 * Interfaces and client for managing gateway connection draining, session state
 * serialization to recovery storage, forensic logging, and zero-loss restarts.
 */

export interface ForensicRecord {
  forensic_id: string;
  reason: string;
  active_sessions_count: number;
  pending_events: number;
  uptime_seconds: number;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface SessionSnapshot {
  session_id: string;
  user_id: string;
  channel: string;
  state_data: Record<string, unknown>;
  last_active: number;
  snapshot_timestamp: number;
}

export interface LifecycleStatus {
  status: string;
  available: boolean;
  is_shutting_down: boolean;
  active_in_flight_count: number;
  active_sessions_count: number;
  registered_adapters_count: number;
  drain_timeout_seconds: number;
  uptime_seconds: number;
  db_pools_closed: boolean;
}

export interface ShutdownResult {
  status: string;
  signal: string;
  stopped_adapters: string[];
  remaining_pending: number;
  snapshots_saved: number;
  forensic_id: string;
  uptime_seconds: number;
  dry_run: boolean;
}

export class GatewayLifecycleClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async initiateShutdown(
    signalType: string = "SIGTERM",
    dryRun: boolean = true
  ): Promise<ShutdownResult> {
    const endpoint = `${this.baseUrl}/gateway/restart/initiate`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        signal_type: signalType,
        dry_run: dryRun,
      }),
    });
    if (resp.status === 503) {
      throw new Error("Graceful restart is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to initiate graceful restart: ${resp.status}`);
    }
    return (await resp.json()) as ShutdownResult;
  }

  async drainConnections(): Promise<{ status: string; remaining_in_flight: number }> {
    const endpoint = `${this.baseUrl}/gateway/restart/drain`;
    const resp = await fetch(endpoint, {
      method: "POST",
    });
    if (resp.status === 503) {
      throw new Error("Graceful restart is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to drain connections: ${resp.status}`);
    }
    return (await resp.json()) as { status: string; remaining_in_flight: number };
  }

  async snapshotSessions(): Promise<{
    status: string;
    snapshots_saved: number;
    files: string[];
  }> {
    const endpoint = `${this.baseUrl}/gateway/restart/snapshot`;
    const resp = await fetch(endpoint, {
      method: "POST",
    });
    if (resp.status === 503) {
      throw new Error("Graceful restart is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to snapshot sessions: ${resp.status}`);
    }
    return (await resp.json()) as {
      status: string;
      snapshots_saved: number;
      files: string[];
    };
  }

  async recoverSessions(): Promise<{
    status: string;
    recovered_sessions: SessionSnapshot[];
    count: number;
  }> {
    const endpoint = `${this.baseUrl}/gateway/restart/recovery`;
    const resp = await fetch(endpoint, {
      method: "GET",
    });
    if (resp.status === 503) {
      throw new Error("Graceful restart is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to recover sessions: ${resp.status}`);
    }
    return (await resp.json()) as {
      status: string;
      recovered_sessions: SessionSnapshot[];
      count: number;
    };
  }

  async getStatus(): Promise<LifecycleStatus> {
    const endpoint = `${this.baseUrl}/gateway/restart/status`;
    const resp = await fetch(endpoint, {
      method: "GET",
    });
    if (resp.status === 503) {
      throw new Error("Graceful restart is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get gateway restart status: ${resp.status}`);
    }
    return (await resp.json()) as LifecycleStatus;
  }
}
