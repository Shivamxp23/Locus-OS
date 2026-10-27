/**
 * SPEC §27.4: TypeScript client for 3-Level Tag Hierarchy & Semantic Indexing (F-0123 / US-97).
 */

export interface TagValidationResultData {
  tag: string;
  is_valid: boolean;
  normalized_tag: string;
  domain: string;
  category?: string;
  instance?: string;
  level: number;
  error?: string;
}

export interface TagIndexRecordData {
  note_path: string;
  raw_tags: string[];
  normalized_tags: string[];
  domain_distribution: Record<string, number>;
}

export interface TagStatusData {
  indexed_notes_count: number;
  custom_mappings_count: number;
  subsystem_enabled: boolean;
  valid_domains: string[];
  feature_enabled?: boolean;
  provider?: string;
}

export interface TagManagerClientOptions {
  sidecarUrl?: string;
}

export class TagManagerClient {
  private readonly baseUrl: string;

  constructor(options: TagManagerClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async normalizeTags(tags: string[]): Promise<{
    raw_tags: string[];
    normalized_tags: string[];
    count: number;
  }> {
    const res = await fetch(`${this.baseUrl}/vault/tags/normalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags }),
    });
    if (!res.ok) {
      throw new Error(`Failed to normalize tags: ${res.status}`);
    }
    return res.json();
  }

  async validateTag(tag: string): Promise<TagValidationResultData> {
    const res = await fetch(`${this.baseUrl}/vault/tags/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tag }),
    });
    if (!res.ok) {
      throw new Error(`Failed to validate tag: ${res.status}`);
    }
    return res.json();
  }

  async indexNote(notePath: string, tags: string[]): Promise<TagIndexRecordData> {
    const res = await fetch(`${this.baseUrl}/vault/tags/index`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note_path: notePath, tags }),
    });
    if (!res.ok) {
      throw new Error(`Failed to index note tags: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<TagStatusData> {
    const res = await fetch(`${this.baseUrl}/vault/tags/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get tag manager status: ${res.status}`);
    }
    return res.json();
  }
}
