/**
 * SPEC §3.8: Tool Call Validation and Loop Guardrails Client.
 * Bridges TypeScript tool execution with Sidecar safety controller,
 * performing parameter schema checks, stall guard detection, and failure streak containment.
 */

export type ValidationAction = "allow" | "warn" | "block" | "halt";

export interface ValidationDecision {
  action: ValidationAction;
  code: string;
  message: string;
  tool_name: string;
  count: number;
  category: string;
  allows_execution: boolean;
  should_halt: boolean;
  validation_errors: string[];
}

export interface ValidationObservation {
  tool_name: string;
  notice?: string | null;
  stub?: string | null;
  is_duplicate: boolean;
  streak_count: number;
}

export interface ToolCallValidationConfig {
  warnings_enabled: boolean;
  hard_stop_enabled: boolean;
  exact_failure_warn_after: number;
  exact_failure_block_after: number;
  same_tool_failure_warn_after: number;
  same_tool_failure_halt_after: number;
  idempotent_no_progress_warn_after: number;
  idempotent_no_progress_block_after: number;
  identical_call_threshold: number;
  max_cycle_period: number;
  max_web_searches_per_turn: number;
  max_subagents_per_turn: number;
}

export class ToolCallValidationClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Validate tool parameters and evaluate pre-execution loop guardrails.
   */
  async validate(
    toolName: string,
    params: Record<string, any> = {},
    schema?: Record<string, any>,
  ): Promise<ValidationDecision> {
    const url = `${this.baseUrl}/tools/validate`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        params,
        schema,
      }),
    });
    if (response.status === 503) {
      throw new Error("tool_call_validation_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Tool call validation failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.decision;
  }

  /**
   * Record tool execution outcome, updating streak counters and cycle history.
   */
  async observe(
    toolName: string,
    params: Record<string, any> = {},
    result?: string,
    failed?: boolean,
  ): Promise<ValidationObservation> {
    const url = `${this.baseUrl}/tools/observe`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        params,
        result,
        failed,
      }),
    });
    if (response.status === 503) {
      throw new Error("tool_call_validation_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Tool observation failed with status ${response.status}`);
    }
    const data = await response.json();
    return data.observation;
  }

  /**
   * Reset turn-local guardrail streaks and loop detection counters.
   */
  async reset(): Promise<boolean> {
    const url = `${this.baseUrl}/tools/reset`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (response.status === 503) {
      throw new Error("tool_call_validation_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Tool reset failed with status ${response.status}`);
    }
    const data = await response.json();
    return Boolean(data.reset);
  }

  /**
   * Fetch current Tool Call Validation configuration and health metrics.
   */
  async getConfig(): Promise<{
    enabled: boolean;
    provider: string;
    config: ToolCallValidationConfig;
    health?: Record<string, any>;
  }> {
    const url = `${this.baseUrl}/tools/validation/config`;
    const response = await fetch(url);
    if (response.status === 503) {
      throw new Error("tool_call_validation_disabled");
    }
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Tool validation config failed with status ${response.status}`);
    }
    return await response.json();
  }

  /**
   * Higher-order wrapper executing a tool call through validation and observation guardrails.
   */
  async executeGuarded<T = string>(
    toolName: string,
    params: Record<string, any>,
    schema: Record<string, any> | undefined,
    executeFn: () => Promise<T>,
  ): Promise<{ result: T; observation: ValidationObservation; decision: ValidationDecision }> {
    const decision = await this.validate(toolName, params, schema);
    if (decision.should_halt) {
      throw new Error(`Tool execution halted by guardrail [${decision.code}]: ${decision.message}`);
    }

    let result: T;
    let failed = false;
    let resultStr = "";

    try {
      result = await executeFn();
      resultStr = typeof result === "string" ? result : JSON.stringify(result);
    } catch (err: any) {
      failed = true;
      resultStr = err.message || String(err);
      await this.observe(toolName, params, resultStr, true);
      throw err;
    }

    const observation = await this.observe(toolName, params, resultStr, failed);
    return { result, observation, decision };
  }
}
