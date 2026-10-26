/**
 * SPEC §13.7 lines 3374-3437:
 * Shell Blocklist Client and Policy Engine (F-0040 / US-72).
 * TypeScript contract and client for inspecting shell commands against
 * destructive patterns, fork bombs, pipe-to-shell, and sensitive user files.
 */

export interface ShellInspectionDecision {
  allowed: boolean;
  command: string;
  violation_type?: string | null;
  reason?: string | null;
  matched_pattern?: string | null;
}

export interface ShellPatternRule {
  type: string;
  description: string;
  pattern: string;
}

export class ShellPolicyClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.7: Inspect shell command against destructive and sensitive patterns.
   */
  async checkCommand(command: string): Promise<ShellInspectionDecision> {
    const url = `${this.baseUrl}/security/shell/check`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command }),
    });
    if (resp.status === 503) {
      // Off switch: allow command to proceed
      return {
        allowed: true,
        command,
        reason: "Shell Blocklist enforcement disabled (off-switch)",
      };
    }
    if (!resp.ok) {
      throw new Error(`Failed to check shell command: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; decision: ShellInspectionDecision };
    return data.decision;
  }

  /**
   * SPEC §13.7: Inspect path against sensitive home dirs and files.
   */
  async checkPath(
    path: string,
    operation: "read" | "write" = "read",
    outsideBoundary: boolean = false
  ): Promise<{ blocked?: boolean; denied?: boolean; reason?: string | null }> {
    const url = `${this.baseUrl}/security/shell/check_path`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, operation, outside_boundary: outsideBoundary }),
    });
    if (resp.status === 503) {
      return { blocked: false, denied: false, reason: null };
    }
    if (!resp.ok) {
      throw new Error(`Failed to check shell path: ${resp.status}`);
    }
    return (await resp.json()) as { blocked?: boolean; denied?: boolean; reason?: string | null };
  }

  /**
   * SPEC §13.7: List active blocked shell patterns.
   */
  async getPatterns(): Promise<ShellPatternRule[]> {
    const url = `${this.baseUrl}/security/shell/patterns`;
    const resp = await fetch(url, { method: "GET" });
    if (resp.status === 503) {
      return [];
    }
    if (!resp.ok) {
      throw new Error(`Failed to fetch shell patterns: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; patterns: ShellPatternRule[] };
    return data.patterns || [];
  }

  /**
   * Creates a beforeToolCall hook for terminal tool execution.
   */
  createBeforeToolCallHook(): (context: {
    toolCall: { name: string };
    args?: unknown;
  }) => Promise<{ block?: boolean; reason?: string } | undefined> {
    return async (context: {
      toolCall: { name: string };
      args?: unknown;
    }): Promise<{ block?: boolean; reason?: string } | undefined> => {
      const toolName = (context.toolCall?.name || "").toLowerCase();
      // Only inspect shell and terminal execution tools
      if (!["run_command", "bash", "shell", "cmd", "terminal", "exec"].includes(toolName)) {
        return undefined;
      }

      const args = context.args as { command?: string; CommandLine?: string; cmd?: string } | undefined;
      const cmd = args?.command || args?.CommandLine || args?.cmd || "";
      if (!cmd) {
        return undefined;
      }

      const decision = await this.checkCommand(cmd);
      if (!decision.allowed) {
        return {
          block: true,
          reason: decision.reason || "Command blocked by security shell blocklist policy",
        };
      }
      return undefined;
    };
  }
}
