/**
 * locus-extension/src/memory-sync.ts
 *
 * TypeScript client for Multi-Source Ingestion Pipelines.
 * Implements Spec §4.7:
 * - Unified SyncPipeline trait & outcome contract.
 * - Three pipeline kinds: Composio (Direct API), Workspace (local), MCP.
 * - Self-healing raw-archive set difference reconciliation.
 */

export type SyncPipelineKind = "composio" | "workspace" | "mcp";

export interface SyncOutcome {
  records_ingested: number;
  more_pending: boolean;
  note?: string;
  cursor?: string;
  errors: string[];
  duration_ms: number;
}

export interface SourceScope {
  tree_scope: string;
  raw_archive_id: string;
  provider: string;
}

export interface MemorySyncConfig {
  enabled: boolean;
  periodic_interval_seconds: number;
  queue_scheduler_interval_seconds: number;
  daily_budget_cap: number;
  state_db_path?: string;
}

export interface PipelineInfo {
  id: string;
  kind: SyncPipelineKind;
  name: string;
  status: Record<string, any>;
}

export class MemorySyncClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * List all registered sync pipelines and status metadata.
   */
  public async listPipelines(): Promise<PipelineInfo[]> {
    const res = await fetch(`${this.baseUrl}/memory/sync/pipelines`);
    if (!res.ok) {
      throw new Error(`Failed to list pipelines: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.pipelines as PipelineInfo[]) || [];
  }

  /**
   * Execute single pipeline tick.
   */
  public async tickPipeline(pipelineId: string): Promise<SyncOutcome> {
    const res = await fetch(`${this.baseUrl}/memory/sync/tick/${encodeURIComponent(pipelineId)}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to tick pipeline ${pipelineId}: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return data.outcome as SyncOutcome;
  }

  /**
   * Execute sync across all registered pipelines.
   */
  public async tickAll(): Promise<Record<string, SyncOutcome>> {
    const res = await fetch(`${this.baseUrl}/memory/sync/tick_all`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to tick all pipelines: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.outcomes as Record<string, SyncOutcome>) || {};
  }

  /**
   * Trigger self-healing reconciliation between on-disk files and memory store.
   */
  public async healSource(source: SourceScope, onDiskFiles: string[]): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/memory/sync/heal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source,
        on_disk_files: onDiskFiles,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to heal source: ${res.statusText} (${res.status})`);
    }
    const data = await res.json();
    return (data.healed_files as string[]) || [];
  }

  /**
   * Get subsystem configuration and metrics.
   */
  public async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/memory/sync/config`);
    if (!res.ok) {
      throw new Error(`Failed to get memory sync config: ${res.statusText} (${res.status})`);
    }
    return await res.json();
  }
}
