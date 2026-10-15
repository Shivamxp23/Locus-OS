/**
 * locus-extension/src/security/file-safety.ts - File Safety Policy TypeScript client.
 *
 * Implements Spec §13.2
 */

export class FileSafetyClient {
  private static BLOCKED_PATTERNS = [".ssh", ".aws", "/etc/shadow", "system32"];

  public static isPathAllowed(pathStr: string, isWrite: boolean = false): boolean {
    const lower = pathStr.toLowerCase().replace(/\\/g, "/");
    if (lower.includes("\0") || lower.includes("..") || lower.includes("%2e%2e")) {
      return false;
    }
    for (const pat of this.BLOCKED_PATTERNS) {
      if (lower.includes(pat)) return false;
    }
    if (isWrite && (lower.startsWith("packages/") || lower === "packages")) {
      return false;
    }
    return true;
  }
}
