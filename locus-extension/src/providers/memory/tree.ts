/**
 * locus-extension/src/providers/memory/tree.ts - Memory Tree Client
 *
 * Implements Spec §4.5 (Hierarchical Memory Tree Cascade).
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

export interface MemoryTreeProvider {
  appendLeaf(treeScope: string, content: string): Promise<TreeNode>;
  search(treeScope: string, query: string, maxResults?: number): Promise<TreeNode[]>;
}

export class RemoteMemoryTreeProvider implements MemoryTreeProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/memory/tree";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async appendLeaf(treeScope: string, content: string): Promise<TreeNode> {
    if (!this.enabled) {
      return {
        id: "disabled",
        tree_scope: treeScope,
        level: 0,
        content,
        children: [],
        token_count: 0,
        created_at: Date.now() / 1000,
        sealed: false,
      };
    }

    try {
      const res = await fetch(`${this.endpoint}/leaf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tree_scope: treeScope, content }),
      });
      return (await res.json()) as TreeNode;
    } catch {
      return {
        id: `local-${Date.now()}`,
        tree_scope: treeScope,
        level: 0,
        content,
        children: [],
        token_count: content.split(/\s+/).length,
        created_at: Date.now() / 1000,
        sealed: false,
      };
    }
  }

  public async search(treeScope: string, query: string, maxResults: number = 5): Promise<TreeNode[]> {
    if (!this.enabled) return [];
    try {
      const res = await fetch(
        `${this.endpoint}/search?scope=${encodeURIComponent(treeScope)}&query=${encodeURIComponent(query)}&limit=${maxResults}`
      );
      if (!res.ok) return [];
      return (await res.json()) as TreeNode[];
    } catch {
      return [];
    }
  }
}
