/**
 * Locus Auxiliary LLM Client (§29.2) TypeScript companion.
 */

export enum AuxiliaryTaskType {
  TITLE_GENERATION = 'title_generation',
  TAG_EXTRACTION = 'tag_extraction',
  NOTE_PARSING = 'note_parsing',
  ERROR_CLASSIFICATION = 'error_classification',
  CONTEXT_SUMMARY = 'context_summary',
  INTENT_ROUTING = 'intent_routing',
}

export interface AuxiliaryLLMResponse {
  taskType: AuxiliaryTaskType;
  content: string;
  tokenUsage: number;
  durationMs: number;
  model: string;
  metadata?: Record<string, any>;
}

export class AuxiliaryLLMClient {
  private callHistory: AuxiliaryLLMResponse[] = [];

  constructor(public defaultModel: string = 'mock-small-fast', public maxTokens: number = 500) {}

  async executeTask(
    taskType: AuxiliaryTaskType,
    prompt: string,
    systemInstruction?: string,
    overrideModel?: string
  ): Promise<AuxiliaryLLMResponse> {
    const startTime = Date.now();
    const model = overrideModel || this.defaultModel;

    let content = `Auxiliary output for ${taskType}: OK`;
    if (taskType === AuxiliaryTaskType.TITLE_GENERATION) {
      content = `Title: ${prompt.slice(0, 30).trim()}...`;
    } else if (taskType === AuxiliaryTaskType.TAG_EXTRACTION) {
      content = '#project #architecture #locus';
    } else if (taskType === AuxiliaryTaskType.CONTEXT_SUMMARY) {
      content = `Summary: Extracted key points (${prompt.length} chars).`;
    }

    const durationMs = Math.max(1, Date.now() - startTime);
    const resp: AuxiliaryLLMResponse = {
      taskType,
      content,
      tokenUsage: Math.min(this.maxTokens, prompt.split(/\s+/).length + content.split(/\s+/).length),
      durationMs,
      model,
      metadata: { promptPreview: prompt.slice(0, 50) },
    };

    this.callHistory.push(resp);
    return resp;
  }

  getTotalTokens(): number {
    return this.callHistory.reduce((acc, cur) => acc + cur.tokenUsage, 0);
  }
}
