/**
 * SPEC §13.10 lines 3599-3668:
 * Message Sanitization Client & Stateless Helpers (F-0043 / US-75).
 * Replaces lone surrogate code points (U+D800-U+DFFF) with U+FFFD to prevent
 * JSON serialization crashes and API dispatch errors.
 */

export const SURROGATE_RE = /[\uD800-\uDFFF]/g;

export function sanitizeSurrogates(text: string): string {
  if (typeof text !== "string") {
    return text;
  }
  return text.replace(SURROGATE_RE, "\uFFFD");
}

export function sanitizeStructureSurrogates<T = unknown>(
  payload: T
): { sanitized: T; found: boolean } {
  let found = false;

  function walk(node: any): any {
    if (typeof node === "string") {
      if (SURROGATE_RE.test(node)) {
        found = true;
        return node.replace(SURROGATE_RE, "\uFFFD");
      }
      return node;
    }

    if (Array.isArray(node)) {
      return node.map((item) => walk(item));
    }

    if (node !== null && typeof node === "object") {
      const out: Record<string, any> = {};
      for (const [k, v] of Object.entries(node)) {
        const cleanK = typeof k === "string" ? sanitizeSurrogates(k) : k;
        out[cleanK] = walk(v);
      }
      return out;
    }

    return node;
  }

  const sanitized = walk(payload);
  return { sanitized, found };
}

export function sanitizeMessages<T extends { content?: any; tool_calls?: any } = any>(
  messages: T[]
): T[] {
  if (!Array.isArray(messages)) {
    return messages;
  }

  return messages.map((msg) => {
    if (!msg || typeof msg !== "object") {
      return msg;
    }

    const copy = { ...msg };

    // 1. Content field
    if (typeof copy.content === "string") {
      copy.content = sanitizeSurrogates(copy.content);
    } else if (Array.isArray(copy.content) || (copy.content && typeof copy.content === "object")) {
      const res = sanitizeStructureSurrogates(copy.content);
      copy.content = res.sanitized;
    }

    // 2. Tool calls
    if (copy.tool_calls) {
      const res = sanitizeStructureSurrogates(copy.tool_calls);
      copy.tool_calls = res.sanitized;
    }

    // 3. Other structured properties
    for (const key of ["reasoning_details", "metadata", "extra"]) {
      if ((copy as any)[key]) {
        const res = sanitizeStructureSurrogates((copy as any)[key]);
        (copy as any)[key] = res.sanitized;
      }
    }

    return copy;
  });
}

export class MessageSanitizerClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async sanitizeText(text: string): Promise<string> {
    const url = `${this.baseUrl}/security/sanitize/text`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (resp.status === 503) {
      // Off switch fallback: return text as-is
      return text;
    }
    if (!resp.ok) {
      throw new Error(`Failed to sanitize text: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; sanitized: string };
    return data.sanitized;
  }

  async sanitizeStructure<T = unknown>(payload: T): Promise<{ sanitized: T; found: boolean }> {
    const url = `${this.baseUrl}/security/sanitize/structure`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    if (resp.status === 503) {
      return { sanitized: payload, found: false };
    }
    if (!resp.ok) {
      throw new Error(`Failed to sanitize structure: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; sanitized: T; found: boolean };
    return { sanitized: data.sanitized, found: data.found };
  }

  async sanitizeMessages<T = unknown>(messages: T[]): Promise<T[]> {
    const url = `${this.baseUrl}/security/sanitize/messages`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    if (resp.status === 503) {
      return messages;
    }
    if (!resp.ok) {
      throw new Error(`Failed to sanitize messages: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; messages: T[] };
    return data.messages || [];
  }
}
