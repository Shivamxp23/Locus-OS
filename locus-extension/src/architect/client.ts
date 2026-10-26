/**
 * SPEC §10.8 lines 6306-6355:
 * Self-Evolving Architect Bot Client (F-0120 / US-66).
 * TypeScript contract and client for signal scanning, candidate improvement review,
 * risk-gated patch application, and outcome history.
 */

export type TargetClass = "config" | "prompt" | "code";
export type RiskClass = "low" | "medium" | "high";

export interface ArchitectCandidate {
  id: str;
  title: string;
  description: string;
  target_class: TargetClass;
  risk_class: RiskClass;
  source_signal: string;
  proposed_diff: Record<string, any>;
  status: "proposed" | "staged" | "applied" | "rejected" | "delegated";
  harness_prompt?: string | null;
  applied_at?: string | null;
  created_at: string;
}

export interface ArchitectScanResult {
  status: "ok" | "error";
  candidates_count: number;
  candidates: ArchitectCandidate[];
}

export interface ArchitectApplyResult {
  status: "ok" | "error";
  outcome: {
    candidate_id: string;
    action: string;
    note: string;
    diff?: Record<string, any>;
    harness_prompt?: string;
  };
}

export class ArchitectClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §10.8 line 6319:
   * Scan signals and propose self-improvement candidates.
   */
  async scan(signals?: Record<string, any>): Promise<ArchitectScanResult> {
    const url = `${this.baseUrl}/architect/scan`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(signals || {}),
    });
    if (resp.status === 503) {
      throw new Error("Architect Bot is disabled (status 503)");
    }
    const data = await resp.json();
    return data as ArchitectScanResult;
  }

  /**
   * SPEC §10.8 lines 6319-6334:
   * Get active candidate patches.
   */
  async getCandidates(): Promise<ArchitectCandidate[]> {
    const url = `${this.baseUrl}/architect/candidates`;
    const resp = await fetch(url);
    if (resp.status === 503) {
      throw new Error("Architect Bot is disabled (status 503)");
    }
    const data = await resp.json();
    return data.candidates as ArchitectCandidate[];
  }

  /**
   * SPEC §10.8 lines 6330-6337:
   * Apply, stage, or delegate candidate patch by ID.
   */
  async applyCandidate(candidateId: string): Promise<ArchitectApplyResult> {
    const url = `${this.baseUrl}/architect/apply`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_id: candidateId }),
    });
    if (resp.status === 503) {
      throw new Error("Architect Bot is disabled (status 503)");
    }
    const data = await resp.json();
    return data as ArchitectApplyResult;
  }

  /**
   * SPEC §10.8 lines 6335-6337:
   * Get history of patches and recorded outcomes.
   */
  async getHistory(): Promise<Array<Record<string, any>>> {
    const url = `${this.baseUrl}/architect/history`;
    const resp = await fetch(url);
    if (resp.status === 503) {
      throw new Error("Architect Bot is disabled (status 503)");
    }
    const data = await resp.json();
    return data.history as Array<Record<string, any>>;
  }
}
type str = string;
