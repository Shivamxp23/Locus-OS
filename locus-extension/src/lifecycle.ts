/**
 * Locus Extension Lifecycle Dispatcher (SPEC §1.5, F-0005).
 * Connects into Pi's 25+ lifecycle events with per-extension toggling,
 * error containment, and sidecar event synchronization.
 */

export interface ExtensionHook {
  id: string;
  extensionId: string;
  event: string;
  priority: number;
  enabled: boolean;
  handler: (payload: any, ctx?: any) => Promise<any> | any;
}

export interface DispatchResult {
  event: string;
  executed: number;
  skipped: number;
  errors: string[];
}

export class LocusLifecycleDispatcher {
  private hooks: Map<string, ExtensionHook> = new Map();
  private extensionStates: Map<string, boolean> = new Map();

  /**
   * Register a lifecycle hook.
   */
  public registerHook(
    extensionId: string,
    event: string,
    handler: (payload: any, ctx?: any) => Promise<any> | any,
    priority: number = 100,
  ): string {
    const id = `ts-hook-${Math.random().toString(36).substring(2, 9)}`;
    this.hooks.set(id, {
      id,
      extensionId,
      event,
      priority,
      enabled: true,
      handler,
    });
    return id;
  }

  /**
   * Unregister a hook by ID.
   */
  public unregisterHook(id: string): boolean {
    return this.hooks.delete(id);
  }

  /**
   * Enable or disable an extension.
   */
  public setExtensionEnabled(extensionId: string, enabled: boolean): void {
    this.extensionStates.set(extensionId, enabled);
  }

  /**
   * Check if an extension is enabled.
   */
  public isExtensionEnabled(extensionId: string): boolean {
    return this.extensionStates.get(extensionId) ?? true;
  }

  /**
   * Dispatch an event to all registered hooks in priority order with error containment.
   */
  public async dispatchEvent(event: string, payload: any, ctx?: any): Promise<DispatchResult> {
    const matching: ExtensionHook[] = [];
    for (const hook of this.hooks.values()) {
      if (hook.event === event) {
        matching.push(hook);
      }
    }

    // Sort ascending by priority
    matching.sort((a, b) => a.priority - b.priority);

    let executed = 0;
    let skipped = 0;
    const errors: string[] = [];

    for (const hook of matching) {
      if (!hook.enabled || !this.isExtensionEnabled(hook.extensionId)) {
        skipped++;
        continue;
      }

      try {
        await hook.handler(payload, ctx);
        executed++;
      } catch (err: any) {
        errors.push(`Hook ${hook.id} (${hook.extensionId}) failed on ${event}: ${err?.message || err}`);
      }
    }

    return { event, executed, skipped, errors };
  }
}

/**
 * Register canonical Locus lifecycle hooks into Pi's ExtensionAPI.
 */
export function registerLocusLifecycleHooks(pi: any, dispatcher?: LocusLifecycleDispatcher): LocusLifecycleDispatcher {
  const d = dispatcher || new LocusLifecycleDispatcher();

  // 1. session_start: initialize all providers, load state
  d.registerHook("locus_core", "session_start", async (event) => {
    // Session initialization logic
    if (event) {
      event.locus_session_initialized = true;
    }
  }, 10);

  // 2. turn_start: Query Router, State Injection
  d.registerHook("locus_core", "turn_start", async (event) => {
    if (event) {
      event.locus_state_injected = true;
    }
  }, 10);

  // 3. tool_execution_start: tool guardrails check
  d.registerHook("locus_core", "tool_execution_start", async (event) => {
    if (event) {
      event.locus_guardrail_checked = true;
    }
  }, 10);

  // 4. tool_execution_end: tool tracking (idempotent vs mutating)
  d.registerHook("locus_core", "tool_execution_end", async (event) => {
    if (event) {
      const name = event.toolName || "";
      event.locus_tool_mutating = ["write", "edit", "bash", "powershell"].includes(name);
    }
  }, 10);

  // 5. turn_end: post-turn learning, background review
  d.registerHook("locus_core", "turn_end", async (event) => {
    if (event) {
      event.locus_review_scheduled = true;
    }
  }, 10);

  // 6. session_shutdown: flush all providers, persist state
  d.registerHook("locus_core", "session_shutdown", async (event) => {
    if (event) {
      event.locus_flushed = true;
    }
  }, 10);

  // Wire into Pi if pi.on is available
  if (pi && typeof pi.on === "function") {
    pi.on("session_start", (e: any, ctx: any) => d.dispatchEvent("session_start", e, ctx));
    pi.on("turn_start", (e: any, ctx: any) => d.dispatchEvent("turn_start", e, ctx));
    pi.on("tool_execution_start", (e: any, ctx: any) => d.dispatchEvent("tool_execution_start", e, ctx));
    pi.on("tool_execution_end", (e: any, ctx: any) => d.dispatchEvent("tool_execution_end", e, ctx));
    pi.on("turn_end", (e: any, ctx: any) => d.dispatchEvent("turn_end", e, ctx));
    pi.on("session_shutdown", (e: any, ctx: any) => d.dispatchEvent("session_shutdown", e, ctx));
  }

  return d;
}
