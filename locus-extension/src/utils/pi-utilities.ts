/**
 * SPEC §24.1 lines 2720-2726: Pi Utilities (Clipboard, Syntax Highlighting, Frontmatter, File Watcher).
 * Client library for interacting with sidecar utilities subsystem.
 */

export interface ClipboardResult {
  status: string;
  characters_count?: number;
  osc52_bytes?: number;
  text?: string;
  timestamp?: number;
}

export interface FrontmatterResult {
  status: string;
  has_frontmatter: boolean;
  metadata: Record<string, unknown>;
  body: string;
}

export interface SyntaxHighlightResult {
  status: string;
  language: string;
  supported: boolean;
  line_count: number;
  tokens: Record<string, number>;
  highlighted: string;
}

export interface FileChangeEvent {
  event: "created" | "modified" | "deleted";
  path: string;
  mtime?: number;
}

export interface WatcherResult {
  status: string;
  changes: FileChangeEvent[];
  count: number;
}

export class PiUtilitiesClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async copy(text: string): Promise<ClipboardResult> {
    const res = await fetch(`${this.baseUrl}/utils/clipboard/copy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }

  async paste(): Promise<ClipboardResult> {
    const res = await fetch(`${this.baseUrl}/utils/clipboard/paste`);
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }

  async parseFrontmatter(content: string): Promise<FrontmatterResult> {
    const res = await fetch(`${this.baseUrl}/utils/frontmatter/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }

  async highlight(code: string, language = "text"): Promise<SyntaxHighlightResult> {
    const res = await fetch(`${this.baseUrl}/utils/syntax/highlight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language }),
    });
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }

  async pollWatcher(): Promise<WatcherResult> {
    const res = await fetch(`${this.baseUrl}/utils/watcher/poll`, {
      method: "POST",
    });
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }

  async getStatus(): Promise<{ clipboard_length: number; supported_languages: string[]; watch_dir: string }> {
    const res = await fetch(`${this.baseUrl}/utils/status`);
    if (res.status === 503) {
      throw new Error("Pi utilities are disabled (HTTP 503)");
    }
    return res.json();
  }
}
