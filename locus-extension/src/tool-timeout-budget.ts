/**
 * SPEC §3.11: Tool Timeout / Budget Client.
 * Bridges TypeScript tool execution with Sidecar timeout budget controller,
 * enforcing execution time bounds derived from OpenHuman tool_timeout.
 */

export type TimeoutAction = "allow" | "enforce" | "bypass";

export interface ToolTimeoutConfig {
  enabled: boolean;
  default_timeout_secs: number;
  max_timeout_secs: number;
  turn_budget_secs?: number | null;
  per_tool_timeouts: Record<string, number>;
}

export interface TimeoutResolution {
  tool_name: string;
  timeout_secs: number;
  remaining_turn_budget_secs?: number | null;
  action: TimeoutAction;
  is_over_budget: boolean;
}

export interface ExecutionBudgetRecord {
  tool_name: string;
  elapsed_secs: number;
  timed_out: boolean;
}

/**
 * Rejects with a clear error if `promise` does not settle within `timeoutMs`.
 * Clears timer on settlement (matching OpenHuman withTimeout.ts).
 */
export async function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  label: string,
): Promise<T> {
  if (timeoutMs <= 0) return promise;

  let timer: any;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`${label} timed out after ${Math.round(timeoutMs / 1000)}s`));
    }, timeoutMs);
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

export class ToolTimeoutBudgetClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Resolve effective timeout in seconds for a specific tool execution.
   */
  async resolveTimeout(
    toolName: string,
    requestedTimeout?: number,
  ): Promise<TimeoutResolution> {
    const url = `${this.baseUrl}/tools/timeout/resolve`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        requested_timeout: requestedTimeout,
      }),
    });

    if (response.status === 503) {
      // Off-switch active; fallback to default unconstrained timeout
      return {
        tool_name: toolName,
        timeout_secs: requestedTimeout ?? 120.0,
        action: "bypass",
        is_over_budget: false,
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to resolve tool timeout (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.resolution;
  }

  /**
   * Record completed execution duration and update turn budget.
   */
  async recordExecution(
    toolName: string,
    elapsedSecs: number,
    timedOut: boolean = false,
  ): Promise<void> {
    const url = `${this.baseUrl}/tools/timeout/record`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        elapsed_secs: elapsedSecs,
        timed_out: timedOut,
      }),
    });

    if (response.status === 503) return;

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to record tool execution (${response.status}): ${errText}`);
    }
  }

  /**
   * Get remaining seconds in current turn budget.
   */
  async getRemainingBudget(): Promise<number | null> {
    const url = `${this.baseUrl}/tools/timeout/remaining`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) return null;

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get remaining budget (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.remaining_turn_budget_secs;
  }

  /**
   * Reset turn budget elapsed time and optionally configure budget limit.
   */
  async resetTurnBudget(totalBudgetSecs?: number): Promise<void> {
    const url = `${this.baseUrl}/tools/timeout/reset`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ total_budget_secs: totalBudgetSecs }),
    });

    if (response.status === 503) return;

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to reset turn budget (${response.status}): ${errText}`);
    }
  }

  /**
   * Execute an asynchronous tool action wrapped with sidecar timeout enforcement.
   */
  async runWithTimeout<T>(
    toolName: string,
    task: () => Promise<T>,
    customTimeoutSecs?: number,
  ): Promise<T> {
    const resolution = await this.resolveTimeout(toolName, customTimeoutSecs);
    if (resolution.is_over_budget) {
      throw new Error(`Tool execution rejected: Turn execution budget exhausted for '${toolName}'`);
    }

    const start = Date.now();
    let timedOut = false;
    try {
      return await withTimeout(task(), Math.round(resolution.timeout_secs * 1000), toolName);
    } catch (err: any) {
      if (err.message && err.message.includes("timed out")) {
        timedOut = true;
      }
      throw err;
    } finally {
      const elapsed = (Date.now() - start) / 1000.0;
      await this.recordExecution(toolName, elapsed, timedOut).catch(() => {});
    }
  }

  /**
   * Query timeout configuration and health status.
   */
  async getConfig(): Promise<{ enabled: boolean; config: ToolTimeoutConfig; provider: string }> {
    const url = `${this.baseUrl}/tools/timeout/config`;
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (response.status === 503) {
      return {
        enabled: false,
        provider: "none",
        config: {
          enabled: false,
          default_timeout_secs: 0,
          max_timeout_secs: 0,
          turn_budget_secs: null,
          per_tool_timeouts: {},
        },
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get timeout config (${response.status}): ${errText}`);
    }

    return await response.json();
  }
}
