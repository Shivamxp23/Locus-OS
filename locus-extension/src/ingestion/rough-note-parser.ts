/**
 * locus-extension/src/ingestion/rough-note-parser.ts - Rough Note Parser TypeScript client.
 *
 * Implements Spec §27.5
 */

export interface ParsedItem {
  title: string;
  isActionable: boolean;
  tags: string[];
}

export class RoughNoteClient {
  public static extractTags(text: string): string[] {
    const matches = text.match(/#([\w/-]+)/g);
    return matches ? matches.map((m) => m.toLowerCase()) : [];
  }
}
