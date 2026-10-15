/**
 * locus-extension/src/providers/harness/harness-provider.ts
 *
 * Implements Spec §3.7, §11.5, and Security Rule S-3.
 * TypeScript harness delegation interface and provider for Pi Agent.
 */

export interface CodingTask {
  taskId?: string;
  prompt: string;
  targetHarness?: "mock" | "pi" | "claude" | "opencode";
  timeoutSeconds?: number;
  preserveWorktree?: boolean;
  metadata?: Record<string, unknown>;
}

export interface DelegationResult {
  taskId: string;
  harness: string;
  worktreePath: string;
  exitCode: number;
  diff: string;
  modifiedFiles: string[];
  stdout: string;
  stderr: string;
  durationMs: number;
  cleanedUp: boolean;
  ok: boolean;
}

export interface HarnessProvider {
  isAvailable(harnessName: string): Promise<boolean>;
  delegate(task: CodingTask): Promise<DelegationResult>;
}

export class RemoteHarnessProvider implements HarnessProvider {
  private endpoint: string;
  private enabled: boolean;

  constructor(options: { endpoint?: string; enabled?: boolean } = {}) {
    this.endpoint = options.endpoint ?? "http://127.0.0.1:8420/harness/delegate";
    this.enabled = options.enabled ?? true;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public async isAvailable(harnessName: string): Promise<boolean> {
    if (!this.enabled) return false;
    try {
      const res = await fetch(`http://127.0.0.1:8420/harness/available?name=${encodeURIComponent(harnessName)}`);
      if (!res.ok) return harnessName === "mock";
      const data = (await res.json()) as { available: boolean };
      return Boolean(data.available);
    } catch {
      return harnessName === "mock";
    }
  }

  public async delegate(task: CodingTask): Promise<DelegationResult> {
    if (!this.enabled) {
      return {
        taskId: task.taskId ?? "disabled",
        harness: task.targetHarness ?? "mock",
        worktreePath: "",
        exitCode: 1,
        diff: "",
        modifiedFiles: [],
        stdout: "",
        stderr: "Harness delegation disabled by configuration.",
        durationMs: 0,
        cleanedUp: true,
        ok: false,
      };
    }

    try {
      const res = await fetch(this.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: task.taskId,
          prompt: task.prompt,
          target_harness: task.targetHarness ?? "mock",
          timeout_seconds: task.timeoutSeconds ?? 120,
          preserve_worktree: task.preserveWorktree ?? false,
          metadata: task.metadata ?? {},
        }),
      });

      if (!res.ok) {
        throw new Error(`Delegation HTTP error: ${res.status}`);
      }

      const json = (await res.json()) as any;
      return {
        taskId: json.task_id ?? task.taskId ?? "",
        harness: json.harness ?? task.targetHarness ?? "mock",
        worktreePath: json.worktree_path ?? "",
        exitCode: json.exit_code ?? 0,
        diff: json.diff ?? "",
        modifiedFiles: json.modified_files ?? [],
        stdout: json.stdout ?? "",
        stderr: json.stderr ?? "",
        durationMs: json.duration_ms ?? 0,
        cleanedUp: json.cleaned_up ?? true,
        ok: (json.exit_code ?? 0) === 0,
      };
    } catch (err: any) {
      return {
        taskId: task.taskId ?? "error",
        harness: task.targetHarness ?? "mock",
        worktreePath: "",
        exitCode: 1,
        diff: "",
        modifiedFiles: [],
        stdout: "",
        stderr: err?.message ?? String(err),
        durationMs: 0,
        cleanedUp: true,
        ok: false,
      };
    }
  }
}
