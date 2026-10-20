/**
 * locus-extension/src/memory-tree.ts
 *
 * TypeScript client for Hierarchical Memory Tree (Summarization Cascade).
 * Implements Spec §4.5:
 * - Generic multi-level summarization tree over text corpora.
 * - L0 leaf buffer -> L1-LN progressive summaries -> Root.
 * - Auto-sealing cascade and top-down relevance search.
 * - Topic routing across scoped trees.
 */

export interface TreeNode {
  id: string;
  tree_scope: string;
  level: number;
  content: string;
  children: string[];
  token_count: number;
  created_at: number;
  sealed: boolean;
}

export interface TreeScopeConfig {
  tree_scope: string;
  seal_gate: number;
  stale_flush_seconds: number;
  max_depth?: number;
}

export interface MemoryTreeConfig {
  enabled: boolean;
  default_seal_gate: number;
  stale_flush_seconds: number;
  db_path?: string;
  max_context_tokens?: number;
}

export interface AppendLeafRequest {
  tree_scope: string;
  content: string;
  source_id?: string;
  source_kind?: string;
}

export interface SealLevelRequest {
  tree_scope: string;
  level?: number;
  force?: boolean;
}

export interface TopicRouteRequest {
  content: string;
  topics: string[];
}

export class MemoryTreeClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Append raw leaf chunk to L0 buffer.
   */
  public async appendLeaf(
    treeScope: string,
    content: string,
    sourceId?: string,
    sourceKind?: string
  ): Promise<TreeNode> {
    const res = await fetch(`${this.baseUrl}/memory/tree/leaf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tree_scope: treeScope,
        content,
        source_id: sourceId,
        source_kind: sourceKind,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to append leaf to memory tree: ${res.statusText} (${res.status})`);
    }

    return (await res.json()) as TreeNode;
  }

  /**
   * Trigger seal operation at a level.
   */
  public async sealLevel(
    treeScope: string,
    level: number = 0,
    force: boolean = false
  ): Promise<TreeNode | null> {
    const res = await fetch(`${this.baseUrl}/memory/tree/seal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tree_scope: treeScope,
        level,
        force,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to seal memory tree level: ${res.statusText} (${res.status})`);
    }

    const data = await res.json();
    return (data.node as TreeNode) ?? null;
  }

  /**
   * Search memory tree with hierarchical relevance ranking.
   */
  public async search(
    treeScope: string,
    query: string,
    maxResults: number = 5
  ): Promise<TreeNode[]> {
    const params = new URLSearchParams({
      tree_scope: treeScope,
      query,
      max_results: String(maxResults),
    });

    const res = await fetch(`${this.baseUrl}/memory/tree/search?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to search memory tree: ${res.statusText} (${res.status})`);
    }

    const data = await res.json();
    return (data.nodes as TreeNode[]) || [];
  }

  /**
   * Route content chunk to matching topic trees.
   */
  public async topicRoute(
    content: string,
    topics: string[]
  ): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/memory/tree/topic_route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        topics,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to route topic: ${res.statusText} (${res.status})`);
    }

    const data = await res.json();
    return (data.matched_scopes as string[]) || [];
  }

  /**
   * Retrieve nodes matching scope and/or level.
   */
  public async getNodes(
    treeScope?: string,
    level?: number
  ): Promise<TreeNode[]> {
    const params = new URLSearchParams();
    if (treeScope !== undefined) params.set("tree_scope", treeScope);
    if (level !== undefined) params.set("level", String(level));

    const res = await fetch(`${this.baseUrl}/memory/tree/nodes?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to get nodes: ${res.statusText} (${res.status})`);
    }

    const data = await res.json();
    return (data.nodes as TreeNode[]) || [];
  }

  /**
   * Get subsystem configuration and metrics.
   */
  public async getConfig(): Promise<MemoryTreeConfig> {
    const res = await fetch(`${this.baseUrl}/memory/tree/config`);
    if (!res.ok) {
      throw new Error(`Failed to get memory tree config: ${res.statusText} (${res.status})`);
    }

    return (await res.json()) as MemoryTreeConfig;
  }
}
