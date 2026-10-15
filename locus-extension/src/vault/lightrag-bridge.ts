/**
 * locus-extension/src/vault/lightrag-bridge.ts - LightRAG Bridge TypeScript client.
 *
 * Implements Spec §30.10
 */

export class LightRAGClient {
  public static extractWikiLinks(text: string): string[] {
    const rx = /\[\[(.*?)\]\]/g;
    const matches: string[] = [];
    let m;
    while ((m = rx.exec(text)) !== null) {
      matches.push(m[1]);
    }
    return matches;
  }
}
