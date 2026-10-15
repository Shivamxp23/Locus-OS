/**
 * System Prompt Construction (§1.2)
 *
 * Constructs composite system prompt injecting SOUL.md, Context Forge, and DCS state.
 */

export interface PromptContextFile {
  path: string;
  content: string;
}

export interface PromptOptions {
  cwd?: string;
  soulOverride?: string;
  appendSystemPrompt?: string;
  contextFiles?: PromptContextFile[];
  skills?: string[];
  selectedTools?: string[];
  promptGuidelines?: string[];
  contextForgeInjection?: string;
  stateInjection?: string;
}

export const DEFAULT_LOCUS_SOUL =
  "You are Locus, a sovereign cognitive operating system and autonomous pair programmer. " +
  "Operate deterministically, respect user autonomy tiers, and maintain persistent state.";

export function buildSystemPrompt(options: PromptOptions = {}): string {
  const cwd = (options.cwd || "/").replace(/\\/g, "/");
  const dateStr = new Date().toISOString();

  const sections: string[] = [];
  sections.push(options.soulOverride || DEFAULT_LOCUS_SOUL);
  sections.push(`Working Directory: ${cwd}\nCurrent Date: ${dateStr}`);

  if (options.stateInjection) {
    sections.push(`<locus_state>\n${options.stateInjection}\n</locus_state>`);
  }

  if (options.contextForgeInjection) {
    sections.push(`<context_forge>\n${options.contextForgeInjection}\n</context_forge>`);
  }

  const tools = options.selectedTools || ["read", "bash", "edit", "write"];
  sections.push("Available Tools:\n" + tools.map(t => `- ${t}`).join("\n"));

  const guidelines = [...(options.promptGuidelines || []), "Be concise and avoid sycophancy."];
  sections.push("Guidelines:\n" + guidelines.map(g => `- ${g}`).join("\n"));

  if (options.contextFiles && options.contextFiles.length > 0) {
    const filesStr = options.contextFiles
      .map(cf => `<file path='${cf.path}'>\n${cf.content}\n</file>`)
      .join("\n");
    sections.push(`<project_context>\n${filesStr}\n</project_context>`);
  }

  if (options.appendSystemPrompt) {
    sections.push(options.appendSystemPrompt);
  }

  return sections.join("\n\n");
}
