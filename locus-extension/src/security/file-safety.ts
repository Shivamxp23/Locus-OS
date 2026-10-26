/**
 * SPEC §13.2 lines 3141-3165:
 * File Safety Client (F-0107 / US-69).
 * TypeScript contract and client for cwd_jail containment,
 * blocked patterns inspection, and file_state tracking.
 */

export interface PathValidationDecision {
  allowed: boolean;
  path: string;
  resolved_path: string;
  operation: string;
  reason?: string | null;
  violation_type?: string | null;
}

export interface FileStateRecord {
  path: string;
  operation: string;
  timestamp: string;
  size_bytes?: number | null;
  sha256?: string | null;
}

export class FileSafetyClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.2: Validate path against cwd_jail and blocked patterns.
   */
  async validatePath(
    path: string,
    operation: string = "read",
    cwd?: string
  ): Promise<PathValidationDecision> {
    const url = `${this.baseUrl}/security/file/validate`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, operation, cwd }),
    });
    if (resp.status === 503) {
      // Off-switch: fallback to default access
      return {
        allowed: true,
        path,
        resolved_path: path,
        operation,
        reason: "off_switch_disabled",
        violation_type: null,
      };
    }
    if (!resp.ok) {
      throw new Error(`Path validation failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; decision: PathValidationDecision };
    return data.decision;
  }

  /**
   * SPEC §13.2: Track file modification.
   */
  async recordModification(
    path: string,
    operation: string = "modify",
    content?: string
  ): Promise<FileStateRecord> {
    const url = `${this.baseUrl}/security/file/record`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, operation, content }),
    });
    if (resp.status === 503) {
      return {
        path,
        operation,
        timestamp: new Date().toISOString(),
      };
    }
    if (!resp.ok) {
      throw new Error(`File modification record failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; record: FileStateRecord };
    return data.record;
  }

  /**
   * SPEC §13.2: Get file state modification history.
   */
  async getHistory(limit: number = 50): Promise<FileStateRecord[]> {
    const url = `${this.baseUrl}/security/file/history?limit=${limit}`;
    const resp = await fetch(url, {
      method: "GET",
    });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`File state history failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; history: FileStateRecord[] };
    return data.history || [];
  }
}
