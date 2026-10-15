/**
 * locus-extension/src/providers/memory/sync/workspace-sync.ts
 *
 * Implements Spec §4.7 (Multi-Source Memory Ingestion Pipelines).
 */

export interface SyncOutcome {
  records_ingested: number;
  more_pending: boolean;
  note?: string;
}

export interface SyncPipeline {
  id(): string;
  kind(): "Workspace" | "Remote" | "Mcp";
  tick(): Promise<SyncOutcome>;
}

export class RemoteWorkspaceSyncPipeline implements SyncPipeline {
  private pipelineId: string;
  private endpoint: string;

  constructor(options: { id?: string; endpoint?: string } = {}) {
    this.pipelineId = options.id ?? "workspace:vault";
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/memory/sync";
  }

  public id(): string {
    return this.pipelineId;
  }

  public kind(): "Workspace" {
    return "Workspace";
  }

  public async tick(): Promise<SyncOutcome> {
    try {
      const res = await fetch(`${this.endpoint}/tick`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_id: this.pipelineId }),
      });
      if (!res.ok) throw new Error(`Sync HTTP error ${res.status}`);
      return (await res.json()) as SyncOutcome;
    } catch (err: any) {
      return {
        records_ingested: 0,
        more_pending: false,
        note: `Sync failed: ${err?.message ?? err}`,
      };
    }
  }
}
