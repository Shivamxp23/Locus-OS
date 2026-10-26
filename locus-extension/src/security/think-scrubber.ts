/**
 * SPEC §13.9 lines 3513-3598:
 * Think Token Scrubbing Client & Streaming State Machine (F-0042 / US-74).
 * Strips <think>, <thinking>, <reasoning>, <thought>, <REASONING_SCRATCHPAD>
 * blocks from streamed assistant output to prevent reasoning leakage.
 */

export const SUPPORTED_TAGS: string[] = [
  "think",
  "thinking",
  "reasoning",
  "thought",
  "REASONING_SCRATCHPAD",
];

export enum ScrubState {
  NORMAL = "NORMAL",
  PENDING_TAG = "PENDING_TAG",
  INSIDE_BLOCK = "INSIDE_BLOCK",
}

export class StreamingThinkScrubber {
  private tags: string[];
  private state: ScrubState;
  private heldBack: string;
  private currentCloseTag: string | null;
  private linePrefix: string;

  constructor(tags: string[] = SUPPORTED_TAGS) {
    this.tags = tags.map((t) => t.toLowerCase());
    this.state = ScrubState.NORMAL;
    this.heldBack = "";
    this.currentCloseTag = null;
    this.linePrefix = "";
  }

  public reset(): void {
    this.state = ScrubState.NORMAL;
    this.heldBack = "";
    this.currentCloseTag = null;
    this.linePrefix = "";
  }

  private isBlockBoundary(): boolean {
    return (
      this.linePrefix === "" ||
      this.linePrefix.trim() === "" ||
      this.linePrefix.endsWith("\n")
    );
  }

  public feed(deltaText: string): string {
    if (!deltaText) return "";

    const result: string[] = [];
    const n = deltaText.length;
    let i = 0;

    while (i < n) {
      const char = deltaText[i];

      if (this.state === ScrubState.NORMAL) {
        if (char === "<") {
          this.state = ScrubState.PENDING_TAG;
          this.heldBack = "<";
        } else {
          result.push(char);
          if (char === "\n") {
            this.linePrefix = "";
          } else {
            this.linePrefix += char;
          }
        }
        i++;
      } else if (this.state === ScrubState.PENDING_TAG) {
        this.heldBack += char;
        i++;
        const hbLower = this.heldBack.toLowerCase();

        let matchedTag: string | null = null;
        for (const t of this.tags) {
          if (hbLower === `<${t}>`) {
            matchedTag = t;
            break;
          }
        }

        if (matchedTag) {
          if (this.isBlockBoundary()) {
            this.state = ScrubState.INSIDE_BLOCK;
            this.currentCloseTag = `</${matchedTag}>`;
            this.heldBack = "";
          } else {
            result.push(this.heldBack);
            this.linePrefix += this.heldBack;
            this.heldBack = "";
            this.state = ScrubState.NORMAL;
          }
        } else if (this.tags.some((t) => `<${t}>`.startsWith(hbLower))) {
          // Keep buffering in PENDING_TAG
        } else {
          result.push(this.heldBack);
          this.linePrefix += this.heldBack;
          this.heldBack = "";
          this.state = ScrubState.NORMAL;
        }
      } else if (this.state === ScrubState.INSIDE_BLOCK) {
        this.heldBack += char;
        i++;
        const hbLower = this.heldBack.toLowerCase();
        const closeTarget = this.currentCloseTag || "</think>";

        if (hbLower.includes(closeTarget)) {
          this.state = ScrubState.NORMAL;
          this.heldBack = "";
          this.currentCloseTag = null;
          this.linePrefix = "";
        } else {
          const maxCloseLen = Math.max(...this.tags.map((t) => t.length)) + 3;
          if (this.heldBack.length > maxCloseLen * 2) {
            this.heldBack = this.heldBack.slice(-maxCloseLen);
          }
        }
      }
    }

    return result.join("");
  }

  public flush(): string {
    if (this.heldBack && this.state === ScrubState.PENDING_TAG) {
      const res = this.heldBack;
      this.heldBack = "";
      this.state = ScrubState.NORMAL;
      return res;
    }
    this.heldBack = "";
    this.state = ScrubState.NORMAL;
    return "";
  }

  public processComplete(text: string): string {
    this.reset();
    return (this.feed(text) + this.flush()).trim();
  }
}

export class ThinkScrubberClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async feed(delta: string): Promise<string> {
    const url = `${this.baseUrl}/security/think_scrubber/feed`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ delta }),
    });
    if (resp.status === 503) {
      // Off switch fallback: pass-through delta untouched
      return delta;
    }
    if (!resp.ok) {
      throw new Error(`Failed to feed think scrubber: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; visible: string };
    return data.visible;
  }

  async flush(): Promise<string> {
    const url = `${this.baseUrl}/security/think_scrubber/flush`;
    const resp = await fetch(url, { method: "POST" });
    if (resp.status === 503) {
      return "";
    }
    if (!resp.ok) {
      throw new Error(`Failed to flush think scrubber: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; visible: string };
    return data.visible;
  }

  async scrubComplete(text: string): Promise<string> {
    const url = `${this.baseUrl}/security/think_scrubber/scrub_complete`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (resp.status === 503) {
      return text;
    }
    if (!resp.ok) {
      throw new Error(`Failed to scrub complete text: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; scrubbed: string };
    return data.scrubbed;
  }

  async reset(): Promise<void> {
    const url = `${this.baseUrl}/security/think_scrubber/reset`;
    await fetch(url, { method: "POST" });
  }

  async getTags(): Promise<string[]> {
    const url = `${this.baseUrl}/security/think_scrubber/tags`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Failed to fetch think scrubber tags: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; tags: string[] };
    return data.tags || [];
  }
}
