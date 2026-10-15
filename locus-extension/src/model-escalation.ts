/**
 * Model Management & Escalation Hook (§1.4).
 *
 * Bridges Pi Agent's prepareNextTurn hook to Locus ModelRouter.
 * Automatically escalates from standard turn models (DeepSeek Flash) to complex reasoning
 * models (Gemini Pro) when task classification or context demands it.
 */

import { ModelRouter, RoutingDecision, TaskCategory } from "./routing/model-router.js";

export interface TurnEscalationContext {
  turn_count: number;
  last_user_prompt: string;
  accumulated_tokens: number;
  active_mode?: string;
}

export class ModelEscalationManager {
  private router: ModelRouter;

  constructor() {
    this.router = new ModelRouter();
  }

  public evaluateEscalation(context: TurnEscalationContext): RoutingDecision {
    // If user prompt triggers complex reasoning or context is deep
    const category: TaskCategory =
      context.accumulated_tokens > 64000 || /architect|synthesis|complex|refactor/i.test(context.last_user_prompt)
        ? "complex_reasoning"
        : "standard_chat";

    return this.router.route(category, {
      estimated_tokens: context.accumulated_tokens,
    });
  }
}
