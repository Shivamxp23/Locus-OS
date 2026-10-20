/**
 * SPEC §3.7a: Git Tools client for Locus Extension.
 * Programmatic Git operations (status, diff, commit, log) with HTTP service bridge
 * and modular 503 off-switch handling.
 */

export interface GitStatusResult {
  branch: string;
  clean: boolean;
  staged: string[];
  unstaged: string[];
  untracked: string[];
  head_commit?: string;
}

export interface GitDiffResult {
  diff: string;
  files_changed: string[];
  insertions: number;
  deletions: number;
}

export interface GitCommitResult {
  success: boolean;
  commit_hash?: string;
  message: string;
  files_committed: string[];
  error?: string;
}

export interface GitLogEntry {
  hash: string;
  author: string;
  date: string;
  message: string;
}

export class GitToolsClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Retrieves status of target repository working tree and staging area.
   */
  async getStatus(repoPath?: string): Promise<GitStatusResult> {
    const url = new URL(`${this.baseUrl}/git/status`);
    if (repoPath) {
      url.searchParams.set("repo_path", repoPath);
    }
    const response = await fetch(url.toString());
    if (response.status === 503) {
      throw new Error("git_tools_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Git status failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.result as GitStatusResult;
  }

  /**
   * Retrieves git diff for working tree or staged changes.
   */
  async getDiff(staged: boolean = false, path?: string, repoPath?: string): Promise<GitDiffResult> {
    const response = await fetch(`${this.baseUrl}/git/diff`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ staged, path, repo_path: repoPath }),
    });
    if (response.status === 503) {
      throw new Error("git_tools_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Git diff failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.result as GitDiffResult;
  }

  /**
   * Stages specified files and creates a new commit with the provided message.
   */
  async commit(message: string, files?: string[], repoPath?: string): Promise<GitCommitResult> {
    if (!message || !message.trim()) {
      throw new Error("Commit message cannot be empty");
    }
    const response = await fetch(`${this.baseUrl}/git/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message.trim(), files, repo_path: repoPath }),
    });
    if (response.status === 503) {
      throw new Error("git_tools_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Git commit failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.result as GitCommitResult;
  }

  /**
   * Queries recent git commit history.
   */
  async getLog(maxCount: number = 10, repoPath?: string): Promise<GitLogEntry[]> {
    const url = new URL(`${this.baseUrl}/git/log`);
    url.searchParams.set("max_count", String(maxCount));
    if (repoPath) {
      url.searchParams.set("repo_path", repoPath);
    }
    const response = await fetch(url.toString());
    if (response.status === 503) {
      throw new Error("git_tools_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Git log failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.log as GitLogEntry[];
  }

  /**
   * Checks Git Tools service configuration and availability.
   */
  async getConfig(): Promise<{ status: string; enabled: boolean; provider?: string }> {
    const response = await fetch(`${this.baseUrl}/git/config`);
    if (response.status === 503) {
      return { status: "disabled", enabled: false };
    }
    if (!response.ok) {
      throw new Error(`Git config failed with status ${response.status}`);
    }
    return await response.json();
  }
}
