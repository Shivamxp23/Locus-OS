/**
 * SPEC §27.6 lines 7254-7304: Link Dump & Web Resource Logger TypeScript client.
 */

export interface LinkResourceSummary {
  url: string;
  title: string;
  domain_category: string;
  key_takeaways: string[];
  relevance_to_goals: string;
  user_commentary: string;
  excerpt: string;
  created_at: string;
  vault_path?: string | null;
}

export interface ProcessLinkDumpRequest {
  url: string;
  user_commentary?: string;
  html_content?: string;
  save_to_vault?: boolean;
  vault_root?: string;
}

export interface ProcessLinkDumpResponse {
  status: string;
  path?: string | null;
  title?: string | null;
  takeaways: string[];
  resource?: LinkResourceSummary | null;
  error?: string | null;
  status_code: number;
}

export interface LinkLoggerStatusResponse {
  subsystem_enabled: boolean;
  timeout_seconds: number;
  supported_categories: string[];
  provider_enabled?: boolean;
  provider_name?: string;
  status_code?: number;
}

export class LinkDumpLoggerClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async processLink(request: ProcessLinkDumpRequest): Promise<ProcessLinkDumpResponse> {
    const response = await fetch(`${this.baseUrl}/ingestion/link/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Link Dump Logger disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as ProcessLinkDumpResponse;
  }

  async getStatus(): Promise<LinkLoggerStatusResponse> {
    const response = await fetch(`${this.baseUrl}/ingestion/link/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      const err = await response.json();
      throw new Error(`Link Dump Logger disabled: ${JSON.stringify(err)}`);
    }

    return (await response.json()) as LinkLoggerStatusResponse;
  }
}
