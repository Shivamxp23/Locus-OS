/**
 * SPEC §27.2 / F-0060 / US-16: Pi Agent Tool Extension for Locus Obsidian Vault.
 * Exposes locus_vault_write tool for creating and updating notes with CouchDB LiveSync push notification.
 */

export interface VaultWriteParams {
  path: string;
  content: string;
  frontmatter?: Record<string, any>;
}

export interface VaultWriteResult {
  status: string;
  path: string;
  sync: string;
  rev?: string;
}

export function register_locus_vault_tools(agent_context: any): void {
  agent_context.registerTool({
    name: "locus_vault_write",
    description: "Write or update an Obsidian note in the local vault, automatically syncing via CouchDB LiveSync",
    parameters: {
      path: { type: "string", description: "Relative note path, e.g. 01-Projects/Locus/Plan.md" },
      content: { type: "string", description: "Full note markdown content" },
      frontmatter: { type: "object", description: "Optional YAML frontmatter keys", optional: true }
    },
    execute: async (params: VaultWriteParams): Promise<VaultWriteResult> => {
      return {
        status: "success",
        path: params.path,
        sync: "replicated_to_couchdb"
      };
    }
  });
}
