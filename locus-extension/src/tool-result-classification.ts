/**
 * SPEC §3.9: Tool Result Classification Client.
 * Bridges TypeScript tool execution with Sidecar result classification,
 * categorizing results into success, failure, or partial outcomes,
 * and identifying side-effects and landed file mutations.
 */

export type ResultClassificationType = "success" | "failure" | "partial";

export interface ToolResultClassification {
  status: ResultClassificationType;
  tool_name: string;
  is_success: boolean;
  is_failure: boolean;
  is_partial: boolean;
  has_side_effect: boolean;
  file_mutation_landed: boolean;
  error_message?: string | null;
  details: Record<string, any>;
}

export interface ToolResultClassificationConfig {
  enabled: boolean;
  detect_file_mutations: boolean;
  detect_side_effects: boolean;
  strict_exit_codes: boolean;
}

export class ToolResultClassificationClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  /**
   * Classify tool execution result into success, failure, or partial.
   */
  async classify(
    toolName: string,
    result: any,
    error?: string,
    exitCode?: number,
    params?: Record<string, any>,
  ): Promise<ToolResultClassification> {
    const url = `${this.baseUrl}/tools/classify-result`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: toolName,
        result,
        error,
        exit_code: exitCode,
        params,
      }),
    });

    if (response.status === 503) {
      // Off switch active; fall back to unclassified optimistic default
      return {
        status: error ? "failure" : "success",
        tool_name: toolName,
        is_success: !error,
        is_failure: Boolean(error),
        is_partial: false,
        has_side_effect: true,
        file_mutation_landed: false,
        error_message: error || null,
        details: { off_switch: true },
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Tool result classification failed (${response.status}): ${errText}`);
    }

    const data = await response.json();
    return data.classification;
  }

  /**
   * Query configuration and health status of the result classification provider.
   */
  async getConfig(): Promise<{ enabled: boolean; config: ToolResultClassificationConfig; provider: string }> {
    const url = `${this.baseUrl}/tools/classification/config`;
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
          detect_file_mutations: false,
          detect_side_effects: false,
          strict_exit_codes: false,
        },
      };
    }

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Failed to get tool classification config (${response.status}): ${errText}`);
    }

    return await response.json();
  }
}
