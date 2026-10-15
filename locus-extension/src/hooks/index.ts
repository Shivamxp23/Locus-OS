/**
 * locus-extension/src/hooks/index.ts - Extension hooks and system prompt transform (§1.2).
 */

import { buildSystemPrompt, PromptOptions } from "../prompt-builder.js";

export { buildSystemPrompt, PromptOptions };

export interface ExtensionHookContext {
  cwd: string;
  session_id: string;
  turn_id?: string;
  active_mode?: string;
  dcs?: number;
  assembled_context?: string;
}

export function transformContextHook(
  basePrompt: string,
  context: ExtensionHookContext
): string {
  const options: PromptOptions = {
    cwd: context.cwd,
    stateInjection: context.dcs !== undefined ? `DCS: ${context.dcs} | Mode: ${context.active_mode || "FLOW"}` : undefined,
    contextForgeInjection: context.assembled_context,
    appendSystemPrompt: basePrompt !== "" ? `\n[Base System Instructions]:\n${basePrompt}` : undefined,
  };
  return buildSystemPrompt(options);
}
