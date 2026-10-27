/**
 * SPEC §27.5 lines 7192-7251: Rough Note Parser & Idea Tracker TypeScript client.
 */

export interface RoughNote {
  title: string;
  primary_tag: string;
  core_proposition: string;
  action_items: string[];
  entities: string[];
  raw_text: string;
  source: string;
  created_at: string;
  vault_path?: string | null;
}

export interface ParseRoughNoteRequest {
  raw_text: string;
  source?: string;
  save_to_vault?: boolean;
  vault_root?: string;
}

export interface ParseRoughNoteResponse {
  success: boolean;
  path?: string | null;
  tasks_created: number;
  note?: RoughNote | null;
  error?: string | null;
  status_code: number;
}

export interface RoughNoteStatusResponse {
  subsystem_enabled: boolean;
  default_source: string;
  known_entities_count: number;
  faction_categories: string[];
  provider_enabled?: boolean;
  provider_name?: string;
  status_code?: number;
}

export class RoughNoteParserClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async parseRoughNote(request: ParseRoughNoteRequest): Promise<ParseRoughNoteResponse> {
    const response = await fetch(`${this.baseUrl}/ingestion/rough-note/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Rough Note Parser disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as ParseRoughNoteResponse;
  }

  async getStatus(): Promise<RoughNoteStatusResponse> {
    const response = await fetch(`${this.baseUrl}/ingestion/rough-note/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Rough Note Parser disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as RoughNoteStatusResponse;
  }
}
