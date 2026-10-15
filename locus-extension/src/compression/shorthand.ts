/**
 * locus-extension/src/compression/shorthand.ts - LOCUS_SHORTHAND TypeScript client.
 *
 * Implements Spec §27.3
 */

export class LocusShorthandClient {
  private static DICT: Record<string, string> = {
    function: "fn",
    implementation: "impl",
    configuration: "cfg",
    parameter: "param",
    return: "ret",
    repository: "repo",
  };

  public static compress(text: string): string {
    let res = text;
    for (const [word, short] of Object.entries(this.DICT)) {
      const rx = new RegExp(`\\b${word}\\b`, "gi");
      res = res.replace(rx, short);
    }
    return res;
  }
}
