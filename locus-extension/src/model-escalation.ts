/**
 * SPEC §1.4 / F-0004: Model Management & Escalation Hook for Pi Agent.
 * Intercepts prepareNextTurn to dynamically escalate model between standard,
 * reasoning (1M context), and auxiliary background tiers.
 */

export interface ModelTierConfig {
  standardModel: string;
  reasoningModel: string;
  backgroundModel: string;
  escalationEnabled: boolean;
}

export const DEFAULT_MODEL_TIERS: ModelTierConfig = {
  standardModel: "deepseek/deepseek-chat",
  reasoningModel: "google/gemini-2.5-pro",
  backgroundModel: "deepseek/deepseek-chat",
  escalationEnabled: true,
};

export interface TurnContext {
  taskType?: string;
  promptLength?: number;
  complexityScore?: number;
  isSundaySynthesis?: boolean;
  isBackground?: boolean;
}

export interface ModelEscalationResult {
  modelId: string;
  swapped: boolean;
  reason: string;
}

export function evaluateTurnModel(
  context: TurnContext,
  config: ModelTierConfig = DEFAULT_MODEL_TIERS
): ModelEscalationResult {
  if (!config.escalationEnabled) {
    return {
      modelId: config.standardModel,
      swapped: false,
      reason: "Escalation disabled; using default base model",
    };
  }

  if (context.isBackground) {
    return {
      modelId: config.backgroundModel,
      swapped: true,
      reason: "Background execution routed to auxiliary client",
    };
  }

  if (
    context.isSundaySynthesis ||
    (context.complexityScore && context.complexityScore >= 7.0) ||
    (context.promptLength && context.promptLength > 64000) ||
    context.taskType === "synthesis"
  ) {
    return {
      modelId: config.reasoningModel,
      swapped: true,
      reason: "Escalated to reasoning model for synthesis or high complexity",
    };
  }

  return {
    modelId: config.standardModel,
    swapped: false,
    reason: "Standard routine turn",
  };
}

/**
 * Pi prepareNextTurn hook adapter.
 */
export async function prepareNextTurnModelEscalation(
  turnContext: TurnContext,
  currentModel: string,
  config: ModelTierConfig = DEFAULT_MODEL_TIERS
): Promise<{ nextModel: string; shouldSwap: boolean }> {
  const result = evaluateTurnModel(turnContext, config);
  return {
    nextModel: result.modelId,
    shouldSwap: result.modelId !== currentModel,
  };
}
