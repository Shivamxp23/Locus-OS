/**
 * locus-extension/src/crawlers/chunker.ts - Document Chunker TypeScript client.
 *
 * Implements Spec §30.1
 */

export interface ChunkMetadata {
  index: number;
  sourceFile: string;
  charCount: number;
}

export class ChunkerClient {
  public static estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }
}
