/**
 * locus-extension/src/ingestion/link-logger.ts - Link Logger TypeScript client.
 *
 * Implements Spec §27.6
 */

export class LinkLoggerClient {
  public static extractUrls(text: string): string[] {
    const rx = /https?:\/\/[^\s<>"')]+/g;
    return text.match(rx) || [];
  }
}
