/**
 * locus-extension/src/tools/excalidraw.ts - Excalidraw TypeScript client.
 *
 * Implements Spec §27.7
 */

export class ExcalidrawClient {
  public static createDocumentHeader(): Record<string, unknown> {
    return {
      type: "excalidraw",
      version: 2,
      source: "https://locus.local",
    };
  }
}
