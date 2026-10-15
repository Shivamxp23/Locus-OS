/**
 * locus-extension/src/context/coding-context.ts - Coding Context TypeScript client.
 *
 * Implements Spec §6.3
 */

export interface RepoSymbol {
  name: string;
  kind: string;
  line: number;
}

export class CodingContextClient {
  public static formatSymbolSignature(sym: RepoSymbol): string {
    return `${sym.kind} ${sym.name} (line ${sym.line})`;
  }
}
