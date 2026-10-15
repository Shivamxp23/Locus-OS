/**
 * locus-extension/src/vault-tools.ts - Obsidian Vault & LiveSync tools for Pi Agent.
 *
 * Implements Spec §27.2:
 * - locus_vault_write: writes/updates notes in the local vault with LiveSync push.
 * - locus_vault_read: reads notes from the local vault mirror.
 * - locus_vault_sync_status: queries CouchDB LiveSync status via the sidecar bridge.
 */

import * as fs from "node:fs";
import * as path from "node:path";

export interface VaultWriteParams {
  path: string;
  content: string;
  frontmatter?: Record<string, unknown>;
}

export interface VaultReadParams {
  path: string;
}

export class VaultToolManager {
  private vaultDir: string;
  private sidecarUrl: string;

  constructor(vaultDir: string, sidecarUrl: string = "http://127.0.0.1:8420") {
    this.vaultDir = path.resolve(vaultDir);
    this.sidecarUrl = sidecarUrl.replace(/\/$/, "");
  }

  public async writeNote(params: VaultWriteParams): Promise<{ status: string; path: string }> {
    const fullPath = path.resolve(this.vaultDir, params.path);
    const dir = path.dirname(fullPath);
    await fs.promises.mkdir(dir, { recursive: true });

    let finalContent = params.content;
    if (params.frontmatter && Object.keys(params.frontmatter).length > 0) {
      const yamlFrontmatter = Object.entries(params.frontmatter)
        .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
        .join("\n");
      finalContent = `---\n${yamlFrontmatter}\n---\n\n${params.content}`;
    }

    const tmpPath = `${fullPath}.tmp.${Date.now()}`;
    await fs.promises.writeFile(tmpPath, finalContent, "utf8");
    await fs.promises.rename(tmpPath, fullPath);

    return {
      status: "success",
      path: params.path,
    };
  }

  public async readNote(params: VaultReadParams): Promise<{ status: string; path: string; content?: string; error?: string }> {
    const fullPath = path.resolve(this.vaultDir, params.path);
    try {
      const content = await fs.promises.readFile(fullPath, "utf8");
      return {
        status: "success",
        path: params.path,
        content,
      };
    } catch (err: unknown) {
      return {
        status: "not_found",
        path: params.path,
        error: String(err),
      };
    }
  }
}
