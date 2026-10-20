/**
 * Locus extension entry point for Pi coding agent.
 */
export const LOCUS_EXTENSION_VERSION = "0.1.0";

export * from "./anti-hallucination";
export * from "./context-forge";
export * from "./context-manager";
export * from "./cost-tracker";
export * from "./git-tools";
export * from "./image-generation";
export * from "./intent-classifier";
export * from "./learning";
export * from "./lifecycle";
export * from "./model-escalation";
export * from "./onboarding";
export * from "./post-turn-reviewer";
export * from "./prompt-builder";
export * from "./rate-limiter";
export * from "./routing";
export * from "./sessions/title-gen";
export * from "./state-engine";
export * from "./streaming-sse";
export * from "./subagents";
export * from "./title-generator";
export * from "./tool-call-validation";
export * from "./ui/setup-wizard";
export * from "./tools/index";
export * from "./tools/locus_vault";
export * from "./tracking/pricing";
export * from "./tracking/rate-limits";
export * from "./tracking/usage";
export * from "./trajectory";

export function activate(pi?: any): void {
  // Locus extension initialization
  if (pi) {
    import("./lifecycle").then(({ registerLocusLifecycleHooks }) => {
      registerLocusLifecycleHooks(pi);
    });
  }
}
