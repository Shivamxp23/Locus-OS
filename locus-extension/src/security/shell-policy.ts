/**
 * Shell Blocklist & Policy (§13.7)
 *
 * Intercepts dangerous terminal commands and path access in beforeToolCall hook.
 */

export const SENSITIVE_DIRS = [".ssh", ".aws", ".gnupg", ".kube", ".docker"];
export const SENSITIVE_FILES = [".bashrc", ".zshrc", ".profile", "id_rsa", "authorized_keys"];

export const BLOCKED_COMMANDS = [
  /\brm\s+-[rRfF]*\s+(/|~|\$HOME)\b/,
  /:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:/,
  /\bmkfs\b/,
  /\bdd\s+if=/,
  />\s*\/dev\/sd/,
];

export class ShellPolicy {
  public isPathBlocked(filePath: string): boolean {
    const norm = filePath.replace(/\\/g, "/");
    const base = norm.split("/").pop() || "";
    if (SENSITIVE_FILES.includes(base)) return true;
    for (const d of SENSITIVE_DIRS) {
      if (norm.includes(`/${d}/`) || norm.endsWith(`/${d}`)) return true;
    }
    return false;
  }

  public isCommandBlocked(command: string): boolean {
    for (const pat of BLOCKED_COMMANDS) {
      if (pat.test(command)) return true;
    }
    return false;
  }
}
