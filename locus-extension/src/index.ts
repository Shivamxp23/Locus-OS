/**
 * Locus extension entry point for Pi coding agent.
 */
export const LOCUS_EXTENSION_VERSION = "0.1.0";

export * from "./context-manager";
export * from "./learning";
export * from "./lifecycle";
export * from "./model-escalation";
export * from "./post-turn-reviewer";
export * from "./prompt-builder";
export * from "./tools/index";
export * from "./tools/locus_vault";
export * from "./trajectory";

export function activate(pi?: any): void {
  // Locus extension initialization
  if (pi) {
    import("./lifecycle").then(({ registerLocusLifecycleHooks }) => {
      registerLocusLifecycleHooks(pi);
    });
  }
}
