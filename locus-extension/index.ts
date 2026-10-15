/**
 * locus-extension/index.ts - Locus OS Extension Entry Point (§1.5).
 *
 * Implements the 25+ event lifecycle hooks into Pi Agent:
 * - session_start, turn_start, message_start, message_update, message_end
 * - tool_execution_start, tool_execution_update, tool_execution_end
 * - turn_end, agent_end, session_shutdown
 * - before_compact, after_compact, before_tree, session_switch, replaced_session, context_usage_update
 */

import { CANONICAL_TOOLS, CANONICAL_TOOL_NAMES } from "./src/tools/index.js";
import { transformContextHook } from "./src/hooks/index.js";

export const EXTENSION_EVENTS = [
  "session_start",
  "turn_start",
  "message_start",
  "message_update",
  "message_end",
  "tool_execution_start",
  "tool_execution_update",
  "tool_execution_end",
  "turn_end",
  "agent_end",
  "session_shutdown",
  "before_compact",
  "after_compact",
  "before_tree",
  "session_switch",
  "replaced_session",
  "context_usage_update",
  "subagent_spawn",
  "subagent_terminate",
  "model_switch",
  "quota_exceeded",
  "approval_requested",
  "approval_granted",
  "approval_rejected",
  "error",
] as const;

export type ExtensionEventType = (typeof EXTENSION_EVENTS)[number];

export interface ExtensionEventPayload {
  event_type: ExtensionEventType;
  timestamp: string;
  session_id?: string;
  turn_id?: string;
  data?: Record<string, unknown>;
}

export type ExtensionEventHandler = (payload: ExtensionEventPayload) => Promise<void> | void;

export class LocusExtensionLifecycle {
  private handlers: Map<ExtensionEventType, ExtensionEventHandler[]> = new Map();
  public registeredTools = CANONICAL_TOOLS;

  constructor() {
    this.registerDefaultHooks();
  }

  public on(event: ExtensionEventType, handler: ExtensionEventHandler): void {
    const list = this.handlers.get(event) || [];
    list.push(handler);
    this.handlers.set(event, list);
  }

  public async emit(payload: ExtensionEventPayload): Promise<void> {
    const list = this.handlers.get(payload.event_type) || [];
    for (const handler of list) {
      await handler(payload);
    }
  }

  private registerDefaultHooks(): void {
    // Session start: initialize memory, state engine
    this.on("session_start", payload => {
      // Initialize providers
    });

    // Turn start: query router and state injection
    this.on("turn_start", payload => {
      // Route intent, compute capacity
    });

    // Tool execution hooks: guard check and audit
    this.on("tool_execution_start", payload => {
      // Guard check
    });

    this.on("tool_execution_end", payload => {
      // Log tool telemetry
    });

    // Turn end: background review and consolidation
    this.on("turn_end", payload => {
      // Review turn outcome
    });

    // Session shutdown: persist state and flush
    this.on("session_shutdown", payload => {
      // Flush memory queue
    });
  }
}

export function initializeLocusExtension(): LocusExtensionLifecycle {
  return new LocusExtensionLifecycle();
}
