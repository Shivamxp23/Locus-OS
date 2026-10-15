/**
 * locus-extension/src/context/references.ts - Context References TypeScript client.
 *
 * Implements Spec §6.2
 */

export class ContextReferenceClient {
  public static extractReferences(prompt: string): string[] {
    const rx = /@(file|symbol|git|diff)\(([^)]*)\)/g;
    const matches: string[] = [];
    let m;
    while ((m = rx.exec(prompt)) !== null) {
      matches.push(m[0]);
    }
    return matches;
  }
}
