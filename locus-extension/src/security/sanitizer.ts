/**
 * Message Sanitization Engine (§13.10)
 *
 * Cleans solitary surrogates and invalid UTF-8 sequences from conversation payloads.
 */

export class MessageSanitizer {
  private surrogateRe = /[\uD800-\uDFFF]/g;

  public sanitizeText(text: string): string {
    return text.replace(this.surrogateRe, "\uFFFD");
  }

  public sanitizeRecursive(obj: unknown): unknown {
    if (typeof obj === "string") {
      return this.sanitizeText(obj);
    } else if (Array.isArray(obj)) {
      return obj.map(item => this.sanitizeRecursive(item));
    } else if (obj !== null && typeof obj === "object") {
      const res: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
        res[k] = this.sanitizeRecursive(v);
      }
      return res;
    }
    return obj;
  }
}
