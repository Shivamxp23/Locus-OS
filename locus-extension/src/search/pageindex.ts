/**
 * SPEC §27.1: TypeScript client for PageIndex Vectorless Retrieval (F-0059 / US-95).
 */

export interface PageIndexNodeData {
  title: string;
  node_id: string;
  line_num: number;
  level: number;
  text: string;
  token_count: number;
  cumulative_token_count: number;
  summary?: string;
  prefix_summary?: string;
  nodes: PageIndexNodeData[];
}

export interface PageIndexDocData {
  doc_name: string;
  line_count: number;
  structure: PageIndexNodeData[];
}

export interface PageIndexSearchResultData {
  doc_name: string;
  leaf_node_id: string;
  leaf_title: string;
  citation_path: string[];
  text: string;
  summary?: string;
  hops: number;
  reasoning_steps: Array<{
    hop: number;
    chosen_id: string;
    chosen_title: string;
    summary?: string;
    level: number;
  }>;
}

export interface PageIndexStatusData {
  cached_docs: string[];
  cached_doc_count: number;
  engine_enabled: boolean;
  feature_enabled?: boolean;
  subsystem_enabled?: boolean;
  provider?: string;
}

export interface PageIndexClientOptions {
  sidecarUrl?: string;
}

export class PageIndexClient {
  private readonly baseUrl: string;

  constructor(options: PageIndexClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async buildTree(
    content: string,
    docName: string = "document.md",
    minNodeToken: number = 50,
    summaryTokenThreshold: number = 200
  ): Promise<PageIndexDocData> {
    const res = await fetch(`${this.baseUrl}/pageindex/build-tree`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        doc_name: docName,
        min_node_token: minNodeToken,
        summary_token_threshold: summaryTokenThreshold,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to build PageIndex tree: ${res.status}`);
    }
    return res.json();
  }

  async retrieve(
    query: string,
    docName?: string,
    treeData?: PageIndexDocData
  ): Promise<PageIndexSearchResultData> {
    const res = await fetch(`${this.baseUrl}/pageindex/retrieve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        doc_name: docName,
        tree_data: treeData,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to retrieve via PageIndex: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<PageIndexStatusData> {
    const res = await fetch(`${this.baseUrl}/pageindex/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get PageIndex status: ${res.status}`);
    }
    return res.json();
  }
}
