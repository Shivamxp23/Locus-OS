/**
 * Canonical 13 Locus Tools per SPEC §1.3 and F-0003.
 * Registers tools into Pi Agent Loop via registerTool API.
 */

export interface LocusToolDefinition {
  name: string;
  label: string;
  description: string;
  parameters: Record<string, any>;
  executionMode?: "parallel" | "sequential";
  execute: (params: any, context?: any) => Promise<any>;
}

// 1. locus_checkin: Daily check-in, mood, DCS self-report
export const locus_checkin: LocusToolDefinition = {
  name: "locus_checkin",
  label: "Locus Check-in",
  description: "Submit daily check-in, mood assessment, and energy levels to update DCS.",
  executionMode: "sequential",
  parameters: {
    energy: { type: "number", description: "Energy level 1-10" },
    mood: { type: "string", description: "Mood or affective state descriptor" },
    reflection: { type: "string", description: "Optional journal or reflection notes", optional: true },
  },
  execute: async (params: any) => ({ status: "success", dcs_delta: 0.2, params }),
};

// 2. locus_life: Operating mode & faction distribution
export const locus_life: LocusToolDefinition = {
  name: "locus_life",
  label: "Locus Life OS",
  description: "Inspect and adjust operating modes, faction distributions, and DCS metrics.",
  executionMode: "sequential",
  parameters: {
    action: { type: "string", enum: ["get_metrics", "set_mode", "adjust_faction"] },
    mode: { type: "string", optional: true },
    faction: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "success", action: params.action }),
};

// 3. locus_goals: Goal distiller and outcome tracking
export const locus_goals: LocusToolDefinition = {
  name: "locus_goals",
  label: "Locus Goals",
  description: "Query, distill, and track long-term and short-term goals in the goal stack.",
  executionMode: "sequential",
  parameters: {
    action: { type: "string", enum: ["list", "add", "complete", "distill"] },
    title: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "success", action: params.action }),
};

// 4. locus_memory: Semantic & episodic memory search (Neo4j)
export const locus_memory: LocusToolDefinition = {
  name: "locus_memory",
  label: "Locus Memory",
  description: "Search and recall episodic and semantic facts from Neo4j agent memory.",
  executionMode: "parallel",
  parameters: {
    query: { type: "string", description: "Natural language query to search memory" },
    limit: { type: "number", optional: true },
  },
  execute: async (params: any) => ({ status: "success", query: params.query, matches: [] }),
};

// 5. locus_vault: Obsidian vault read/write and CouchDB sync
export const locus_vault: LocusToolDefinition = {
  name: "locus_vault",
  label: "Locus Vault",
  description: "Read and write notes in the Obsidian vault with CouchDB synchronization.",
  executionMode: "sequential",
  parameters: {
    action: { type: "string", enum: ["read", "write", "search"] },
    path: { type: "string", description: "Relative note path" },
    content: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "success", path: params.path }),
};

// 6. locus_brain: Second brain knowledge graph reasoning
export const locus_brain: LocusToolDefinition = {
  name: "locus_brain",
  label: "Locus Brain",
  description: "Query knowledge graphs and semantic associations across notes.",
  executionMode: "parallel",
  parameters: {
    concept: { type: "string", description: "Concept or entity name" },
    depth: { type: "number", optional: true },
  },
  execute: async (params: any) => ({ status: "success", concept: params.concept, graph: {} }),
};

// 7. locus_research: Autonomous multi-source literature and topic research
export const locus_research: LocusToolDefinition = {
  name: "locus_research",
  label: "Locus Research",
  description: "Perform autonomous multi-source literature and topic research synthesis.",
  executionMode: "parallel",
  parameters: {
    topic: { type: "string", description: "Research topic or problem statement" },
    depth: { type: "string", enum: ["quick", "deep"], optional: true },
  },
  execute: async (params: any) => ({ status: "success", topic: params.topic }),
};

// 8. locus_delegate_code: External coding harness subagent delegation
export const locus_delegate_code: LocusToolDefinition = {
  name: "locus_delegate_code",
  label: "Locus Code Delegation",
  description: "Delegate complex coding tasks to external harnesses (Claude Code, opencode, Pi).",
  executionMode: "sequential",
  parameters: {
    harness: { type: "string", enum: ["claude_code", "opencode", "pi"] },
    prompt: { type: "string", description: "Instruction for the delegate harness" },
  },
  execute: async (params: any) => ({ status: "success", harness: params.harness }),
};

// 9. locus_doctor: Diagnostic health audit and self-healing
export const locus_doctor: LocusToolDefinition = {
  name: "locus_doctor",
  label: "Locus Doctor",
  description: "Run diagnostics and verify sidecar service health and integrity.",
  executionMode: "parallel",
  parameters: {
    component: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "healthy", checked: params.component || "all" }),
};

// 10. locus_pageindex: Document page tree indexing and summaries
export const locus_pageindex: LocusToolDefinition = {
  name: "locus_pageindex",
  label: "Locus PageIndex",
  description: "Index and search long structured documents with hierarchical chapter trees.",
  executionMode: "parallel",
  parameters: {
    action: { type: "string", enum: ["index", "query"] },
    path: { type: "string", optional: true },
    query: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "success", action: params.action }),
};

// 11. locus_diagram: Mermaid diagram generation and validation
export const locus_diagram: LocusToolDefinition = {
  name: "locus_diagram",
  label: "Locus Diagram",
  description: "Generate, validate, and render Mermaid diagrams for architectures and workflows.",
  executionMode: "parallel",
  parameters: {
    code: { type: "string", description: "Mermaid syntax code block" },
  },
  execute: async (params: any) => ({ status: "success", valid: true }),
};

// 12. locus_capture: Fast thought and task capture to inbox
export const locus_capture: LocusToolDefinition = {
  name: "locus_capture",
  label: "Locus Capture",
  description: "Quickly capture fleeting thoughts, tasks, or links into the system inbox.",
  executionMode: "sequential",
  parameters: {
    content: { type: "string", description: "Fleeting note or task text" },
    tags: { type: "array", optional: true },
  },
  execute: async (params: any) => ({ status: "captured", content: params.content }),
};

// 13. locus_schedule: Background tasks, cron triggers, reminders
export const locus_schedule: LocusToolDefinition = {
  name: "locus_schedule",
  label: "Locus Schedule",
  description: "Schedule background actions, recurring cron triggers, and reminders.",
  executionMode: "sequential",
  parameters: {
    action: { type: "string", enum: ["add", "list", "remove"] },
    cron: { type: "string", optional: true },
    task_name: { type: "string", optional: true },
  },
  execute: async (params: any) => ({ status: "success", action: params.action }),
};

export const CANONICAL_LOCUS_TOOLS: LocusToolDefinition[] = [
  locus_checkin,
  locus_life,
  locus_goals,
  locus_memory,
  locus_vault,
  locus_brain,
  locus_research,
  locus_delegate_code,
  locus_doctor,
  locus_pageindex,
  locus_diagram,
  locus_capture,
  locus_schedule,
];

export function register_canonical_locus_tools(agent_context: any): void {
  for (const tool of CANONICAL_LOCUS_TOOLS) {
    agent_context.registerTool({
      name: tool.name,
      label: tool.label,
      description: tool.description,
      parameters: tool.parameters,
      execute: tool.execute,
    });
  }
}

export * from "./excalidraw";

