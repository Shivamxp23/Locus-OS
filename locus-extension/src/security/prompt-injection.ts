/**
 * SPEC §13.1 lines 3006-3140:
 * Prompt Injection Protection Client (F-0037 / US-68).
 * TypeScript contract and client for prompt screening, Unicode normalization,
 * tool definition scanning, and PII-safe audit.
 */

export interface NormalizedPrompt {
  lowered: string;
  collapsed: string;
  compact: string;
  had_zwsp: boolean;
  has_base64_marker: boolean;
  has_instruction_override: boolean;
  has_exfiltration_intent: boolean;
}

export type InjectionVerdict = "Allow" | "Review" | "Block";
export type InjectionAction = "Allow" | "ReviewBlocked" | "Blocked";

export interface PromptEnforcementDecision {
  verdict: InjectionVerdict;
  action: InjectionAction;
  score: number;
  reasons: string[];
  prompt_hash: string;
  prompt_chars: number;
}

export class PromptInjectionClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  /**
   * SPEC §13.1: Screen prompt input before model or tool execution.
   */
  async enforce(
    inputText: string,
    context?: Record<string, any>
  ): Promise<PromptEnforcementDecision> {
    const url = `${this.baseUrl}/security/injection/enforce`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_text: inputText, context }),
    });
    if (resp.status === 503) {
      // Off-switch: pass through unsanitized
      return {
        verdict: "Allow",
        action: "Allow",
        score: 0.0,
        reasons: ["off_switch_disabled"],
        prompt_hash: "",
        prompt_chars: inputText.length,
      };
    }
    if (!resp.ok) {
      throw new Error(`Prompt injection enforce failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; decision: PromptEnforcementDecision };
    return data.decision;
  }

  /**
   * SPEC §13.1 BONUS: Scan tool definition before registering into MCP registry.
   */
  async scanTool(name: string, description: string): Promise<PromptEnforcementDecision> {
    const url = `${this.baseUrl}/security/injection/scan_tool`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    if (resp.status === 503) {
      return {
        verdict: "Allow",
        action: "Allow",
        score: 0.0,
        reasons: ["off_switch_disabled"],
        prompt_hash: "",
        prompt_chars: (name + " " + description).length,
      };
    }
    if (!resp.ok) {
      throw new Error(`Tool scan failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; decision: PromptEnforcementDecision };
    return data.decision;
  }

  /**
   * SPEC §13.1 Step 1: Normalize prompt.
   */
  async normalize(inputText: string): Promise<NormalizedPrompt> {
    const url = `${this.baseUrl}/security/injection/normalize`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_text: inputText }),
    });
    if (!resp.ok) {
      throw new Error(`Prompt normalize failed with status ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; normalized: NormalizedPrompt };
    return data.normalized;
  }
}
