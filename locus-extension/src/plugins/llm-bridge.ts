/**
 * Locus Plugin LLM Sandboxing & Auxiliary Bridge (§9.9) TypeScript companion.
 */

export interface PluginQuotaPolicy {
  maxRequestsPerMinute?: number;
  maxTokensPerHour?: number;
  allowedModels?: string[];
  requireApprovalAboveTokens?: number;
}

export class PluginLLMBridge {
  private pluginPolicies: Map<string, PluginQuotaPolicy> = new Map();
  private pluginUsage: Map<string, { tokensUsed: number; requestsCount: number; lastRequestTime: number }> = new Map();

  constructor(
    public defaultPolicy: PluginQuotaPolicy = {
      maxRequestsPerMinute: 30,
      maxTokensPerHour: 50000,
      allowedModels: ['mock-small-fast', 'claude-3-haiku'],
      requireApprovalAboveTokens: 2000,
    }
  ) {}

  registerPlugin(pluginId: string, policy?: PluginQuotaPolicy): void {
    this.pluginPolicies.set(pluginId, policy || this.defaultPolicy);
    this.pluginUsage.set(pluginId, { tokensUsed: 0, requestsCount: 0, lastRequestTime: 0 });
  }

  async generateCompletion(
    pluginId: string,
    prompt: string,
    model: string = 'mock-small-fast',
    maxTokens: number = 500
  ): Promise<Record<string, any>> {
    if (!this.pluginPolicies.has(pluginId)) {
      this.registerPlugin(pluginId);
    }

    const policy = this.pluginPolicies.get(pluginId)!;
    const usage = this.pluginUsage.get(pluginId)!;
    const now = Date.now();

    const allowed = policy.allowedModels || ['mock-small-fast'];
    if (!allowed.includes(model)) {
      return { success: false, error: `Model '${model}' not permitted for plugin.` };
    }

    const minInterval = (60 / (policy.maxRequestsPerMinute || 30)) * 1000;
    if (now - usage.lastRequestTime < minInterval) {
      return { success: false, error: 'Rate limit exceeded for plugin' };
    }

    const sanitized = prompt.replace(/<<SYS>>/g, '').replace(/<\|im_start\|>/g, '');
    const completion = `Plugin [${pluginId}] LLM Response for: ${sanitized.slice(0, 40)}...`;
    const tokens = prompt.split(/\s+/).length + completion.split(/\s+/).length;

    usage.tokensUsed += tokens;
    usage.requestsCount += 1;
    usage.lastRequestTime = now;

    return {
      success: true,
      pluginId,
      model,
      completion,
      tokensConsumed: tokens,
    };
  }
}
