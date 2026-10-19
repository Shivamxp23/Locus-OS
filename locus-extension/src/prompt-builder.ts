/**
 * Locus System Prompt Construction (SPEC §1.2, F-0002).
 * Canonical location: locus-extension/src/prompt-builder.ts
 */

export interface ContextFile {
  path: string;
  content: string;
}

export interface SkillSummary {
  name: string;
  description: string;
}

export interface OperatingState {
  dcs: number;
  operatingMode: string;
  factionStatus: Record<string, number>;
}

export interface BuildSystemPromptOptions {
  cwd: string;
  customPrompt?: string;
  appendSystemPrompt?: string;
  contextFiles?: ContextFile[];
  skills?: SkillSummary[];
  selectedTools?: string[];
  promptGuidelines?: string[];
  soulContext?: string;
  contextForgeTokens?: string;
  operatingState?: OperatingState;
}

export const DEFAULT_SOUL_PERSONALITY =
  "You are Locus, a personal cognitive operating system and autonomous intelligence partner.\n" +
  "You operate in high-agency, low-friction alignment with your owner's long-term outcomes and daily priorities.\n" +
  "Communicate directly, concisely, and execute tasks with rigorous precision.";

export function buildSystemPrompt(options: BuildSystemPromptOptions): string {
  // SPEC §1.2 line 366: Resolve CWD with forward slashes
  const promptCwd = options.cwd.replace(/\\/g, "/");
  const dateStr = new Date().toISOString();

  const sections: string[] = [];

  // Determine primary persona / body
  if (options.customPrompt) {
    sections.push(options.customPrompt);
  } else {
    // SPEC §1.2 line 409: Replace generic body with Locus SOUL personality
    sections.push(options.soulContext || DEFAULT_SOUL_PERSONALITY);

    const tools = options.selectedTools || ["read", "bash", "edit", "write"];
    const toolsList = tools.map((t) => `- ${t}`).join("\n");
    sections.push(`Available tools:\n${toolsList}`);

    const guidelines: string[] = [];
    if (tools.includes("bash") && !tools.some((t) => ["grep", "find", "ls"].includes(t))) {
      guidelines.push("Use bash for file operations like ls, rg, find");
    }
    if (options.promptGuidelines) {
      guidelines.push(...options.promptGuidelines);
    }
    guidelines.push("Be concise in your responses");
    guidelines.push("Show file paths clearly when working with files");
    sections.push("Guidelines:\n" + guidelines.map((g) => `- ${g}`).join("\n"));
  }

  // State Engine injection
  if (options.operatingState) {
    const factions = Object.entries(options.operatingState.factionStatus)
      .map(([k, v]) => `${k}: ${v.toFixed(1)}%`)
      .join(", ");
    sections.push(
      `<state_engine_status>\n` +
      `Daily Capacity Score (DCS): ${options.operatingState.dcs.toFixed(1)} / 10.0\n` +
      `Active Operating Mode: ${options.operatingState.operatingMode}\n` +
      `Faction Allocation: ${factions}\n` +
      `</state_engine_status>`
    );
  }

  // Context Forge injection
  if (options.contextForgeTokens) {
    sections.push(`<context_forge>\n${options.contextForgeTokens}\n</context_forge>`);
  }

  // Extra prompt append
  if (options.appendSystemPrompt) {
    sections.push(options.appendSystemPrompt);
  }

  // Context files wrapped in XML
  if (options.contextFiles && options.contextFiles.length > 0) {
    const ctx = options.contextFiles
      .map((cf) => `<project_instructions path='${cf.path}'>\n${cf.content}\n</project_instructions>`)
      .join("\n");
    sections.push(`<project_context>\n${ctx}\n</project_context>`);
  }

  // Skills
  const tools = options.selectedTools || ["read", "bash", "edit", "write"];
  if (tools.includes("read") && options.skills && options.skills.length > 0) {
    const skillLines = options.skills.map((s) => `- ${s.name}: ${s.description}`).join("\n");
    sections.push(`<available_skills>\n${skillLines}\n</available_skills>`);
  }

  sections.push(`Current date: ${dateStr}`);
  sections.push(`Current working directory: ${promptCwd}`);

  return sections.join("\n\n");
}
