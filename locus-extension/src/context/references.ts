/**
 * Dynamic Context References Contract (SPEC §6.2: Dynamic Context References (@file, @symbol, @git, @diff)).
 * Maps to canonical locus-extension/src/context/references.ts and sidecar endpoints:
 *   GET /context/references/config
 *   POST /context/references/resolve
 *   POST /context/references/format-xml
 */

export type ContextRefType =
  | "@file"
  | "@dir"
  | "@symbol"
  | "@git"
  | "@diff"
  | "@url";

export interface ResolvedReference {
  ref_type: ContextRefType;
  target_path: string;
  content: string;
  token_count: number;
  truncated: boolean;
}

export interface ResolveReferencesRequest {
  prompt: string;
  max_budget?: number; // default: 1500
}

export interface ResolveReferencesResponse {
  status: string;
  clean_prompt: string;
  references: ResolvedReference[];
  xml_enclosure: string;
}

export class ContextReferenceResolverClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async getConfig(): Promise<Record<string, any>> {
    const res = await fetch(`${this.baseUrl}/context/references/config`);
    if (!res.ok) {
      throw new Error(`getConfig failed with status ${res.status}`);
    }
    return (await res.json()) as Record<string, any>;
  }

  async resolveReferences(
    prompt: string,
    maxBudget: number = 1500
  ): Promise<ResolveReferencesResponse> {
    const res = await fetch(`${this.baseUrl}/context/references/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, max_budget: maxBudget }),
    });
    if (!res.ok) {
      throw new Error(`resolveReferences failed with status ${res.status}`);
    }
    return (await res.json()) as ResolveReferencesResponse;
  }

  async formatXml(references: ResolvedReference[]): Promise<string> {
    const res = await fetch(`${this.baseUrl}/context/references/format-xml`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ references }),
    });
    if (!res.ok) {
      throw new Error(`formatXml failed with status ${res.status}`);
    }
    const data = (await res.json()) as { xml: string };
    return data.xml;
  }
}
