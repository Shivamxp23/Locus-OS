/**
 * SPEC §2.7-2.8 / F-0096 / US-37: Intelligent Model Router Implementation.
 * Orchestrates classification, decision, dispatch, quality fallback, and telemetry.
 */

import { LocalHealthChecker } from "./health";
import { classify, decide, normalizeModelId } from "./policy";
import { isLowQuality } from "./quality";
import {
  ChatRequest,
  ChatResponse,
  RoutingConfig,
  RoutingDecision,
  RoutingRecord,
  DEFAULT_ROUTING_CONFIG,
} from "./types";

export class IntelligentModelRouter {
  private healthChecker: LocalHealthChecker;
  private config: RoutingConfig;
  private history: RoutingRecord[] = [];

  constructor(config: Partial<RoutingConfig> = {}) {
    this.config = { ...DEFAULT_ROUTING_CONFIG, ...config };
    this.healthChecker = new LocalHealthChecker(this.config);
  }

  getHealthChecker(): LocalHealthChecker {
    return this.healthChecker;
  }

  getConfig(): RoutingConfig {
    return { ...this.config };
  }

  updateConfig(updates: Partial<RoutingConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  classify(modelString: string) {
    return classify(modelString);
  }

  normalizeModel(hintOrModel: string): string {
    return normalizeModelId(hintOrModel);
  }

  async getDecision(req: ChatRequest): Promise<RoutingDecision> {
    const category = classify(req.model);
    const health = await this.healthChecker.checkHealth();
    const hasTools = Boolean(req.tools && req.tools.length > 0);
    return decide(category, health.healthy, req.hints, hasTools, this.config);
  }

  /**
   * SPEC §2.7-2.8 DISPATCH FLOW (provider.rs):
   * 1. decision = decide(classify(request.model), health.check(), hints)
   * 2. Primary attempt
   * 3. Fallback on error (if local primary and not privacyRequired)
   * 4. Quality gate (only for local primary): if low quality and not privacyRequired -> fallback
   * 5. Emit RoutingRecord telemetry
   */
  async routeChat(
    req: ChatRequest,
    dispatchers: {
      callLocal: (r: ChatRequest) => Promise<ChatResponse>;
      callRemote: (r: ChatRequest) => Promise<ChatResponse>;
    }
  ): Promise<{ response: ChatResponse; record: RoutingRecord }> {
    const start = Date.now();
    const category = classify(req.model);
    const health = await this.healthChecker.checkHealth();
    const hasTools = Boolean(req.tools && req.tools.length > 0);
    const decision = decide(category, health.healthy, req.hints, hasTools, this.config);

    let usedFallback = false;
    let target = decision.primary;
    let response: ChatResponse;

    try {
      if (decision.primary === "local") {
        response = await dispatchers.callLocal(req);
      } else {
        response = await dispatchers.callRemote(req);
      }
    } catch (primaryErr) {
      if (decision.primary === "local" && decision.fallback === "remote") {
        response = await dispatchers.callRemote(req);
        usedFallback = true;
        target = "remote";
      } else {
        throw primaryErr;
      }
    }

    // Quality gate for local primary
    if (
      decision.primary === "local" &&
      !usedFallback &&
      !req.hints?.privacyRequired &&
      decision.fallback === "remote"
    ) {
      if (isLowQuality(response.text, this.config.minResponseBytes)) {
        response = await dispatchers.callRemote(req);
        usedFallback = true;
        target = "remote";
      }
    }

    const latencyMs = Date.now() - start;
    const tokensIn = response.usage?.promptTokens || 0;
    const tokensOut = response.usage?.completionTokens || 0;
    const estimatedCost =
      target === "remote" ? tokensIn * 0.00000014 + tokensOut * 0.00000028 : 0.0;

    const record: RoutingRecord = {
      category,
      target,
      resolvedModel: response.model || decision.resolvedModel,
      healthStatus: health.healthy,
      usedFallback,
      latencyMs,
      tokensIn,
      tokensOut,
      estimatedCost,
    };

    this.history.push(record);
    return { response, record };
  }

  getHistory(): RoutingRecord[] {
    return [...this.history];
  }
}
