/**
 * SPEC §13.8 lines 3438-3512:
 * Data Redaction and Secret Masking Client (F-0041 / US-73).
 * TypeScript contract and client for scrubbing API keys, bearer tokens,
 * passwords, JWTs, and sensitive query parameters from logs and tool results.
 */

export function maskToken(token: string): string {
  if (!token) {
    return "***REDACTED***";
  }
  const s = token.trim();
  if (s.length < 18) {
    return "***REDACTED***";
  }
  return `${s.slice(0, 6)}...${s.slice(-4)}`;
}

export interface RedactionPattern {
  vendor: string;
  pattern: string;
}

export class DataRedactionClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.8: Redact sensitive API keys and tokens from text.
   */
  async redactText(text: string): Promise<string> {
    const url = `${this.baseUrl}/security/redact/text`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (resp.status === 503) {
      // Off switch fallback: return unredacted text
      return text;
    }
    if (!resp.ok) {
      throw new Error(`Failed to redact text: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; redacted: string };
    return data.redacted;
  }

  /**
   * SPEC §13.8: Redact sensitive keys in nested JSON structures.
   */
  async redactStructure<T = unknown>(payload: T): Promise<T> {
    const url = `${this.baseUrl}/security/redact/structure`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    if (resp.status === 503) {
      return payload;
    }
    if (!resp.ok) {
      throw new Error(`Failed to redact structure: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; redacted: T };
    return data.redacted;
  }

  /**
   * SPEC §13.8: List active vendor and custom redaction patterns.
   */
  async getPatterns(): Promise<RedactionPattern[]> {
    const url = `${this.baseUrl}/security/redact/patterns`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Failed to fetch redaction patterns: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; patterns: RedactionPattern[] };
    return data.patterns || [];
  }

  /**
   * Creates an afterToolCall hook to scrub secrets from tool output text blocks.
   */
  createAfterToolCallHook(): (context: {
    result?: { content?: Array<{ type: string; text?: string }> };
  }) => Promise<{ content?: Array<{ type: string; text?: string }> } | undefined> {
    return async (context: {
      result?: { content?: Array<{ type: string; text?: string }> };
    }): Promise<{ content?: Array<{ type: string; text?: string }> } | undefined> => {
      const content = context.result?.content;
      if (!Array.isArray(content) || content.length === 0) {
        return undefined;
      }

      let mutated = false;
      const scrubbedContent = await Promise.all(
        content.map(async (block) => {
          if (block.type === "text" && block.text) {
            const redacted = await this.redactText(block.text);
            if (redacted !== block.text) {
              mutated = true;
              return { ...block, text: redacted };
            }
          }
          return block;
        })
      );

      if (mutated) {
        return { content: scrubbedContent };
      }
      return undefined;
    };
  }
}
