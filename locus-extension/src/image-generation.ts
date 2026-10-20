/**
 * SPEC §2.9 / F-0098 / US-38: Image Generation TypeScript Client.
 * Connects Pi agent extension to sidecar image generation endpoints
 * with model catalog queries and parameter validation.
 */

export interface ImageGenerationOptions {
  prompt: string;
  model?: string;
  size?: string;
  format?: "png" | "jpeg" | "webp";
  quality?: "standard" | "hd";
  negativePrompt?: string;
  seed?: number;
}

export interface GeneratedImage {
  imageId: string;
  b64Data: string;
  mimeType: string;
  format: string;
  modelUsed: string;
  prompt: string;
  size: string;
  createdAt: number;
}

export interface ImageModelInfo {
  modelId: string;
  provider: string;
  supportedSizes: string[];
  defaultSize: string;
  supportsNegativePrompt: boolean;
  supportsSeed: boolean;
}

export interface ImageGenerationConfig {
  enabled: boolean;
  sidecarBaseUrl: string;
  defaultModel: string;
}

export const DEFAULT_IMAGE_CONFIG: ImageGenerationConfig = {
  enabled: true,
  sidecarBaseUrl: "http://127.0.0.1:8420",
  defaultModel: "openai/dall-e-3",
};

export class ImageGenerationClient {
  private config: ImageGenerationConfig;

  constructor(config: Partial<ImageGenerationConfig> = {}) {
    this.config = { ...DEFAULT_IMAGE_CONFIG, ...config };
  }

  isEnabled(): boolean {
    return this.config.enabled;
  }

  async listModels(): Promise<ImageModelInfo[]> {
    if (!this.config.enabled) {
      throw new Error("Image generation is disabled via locus.images.enabled");
    }

    const res = await fetch(`${this.config.sidecarBaseUrl}/images/models`);
    if (!res.ok) {
      throw new Error(`Failed to list image models: HTTP ${res.status}`);
    }
    const data = (await res.json()) as { models: ImageModelInfo[] };
    return data.models;
  }

  async generateImage(options: ImageGenerationOptions): Promise<GeneratedImage> {
    if (!this.config.enabled) {
      throw new Error("Image generation is disabled via locus.images.enabled");
    }

    const prompt = (options.prompt || "").trim();
    if (!prompt) {
      throw new Error("Image generation prompt cannot be empty or whitespace only");
    }

    const payload = {
      prompt,
      model: options.model || this.config.defaultModel,
      size: options.size || "1024x1024",
      format: options.format || "png",
      quality: options.quality || "standard",
      negative_prompt: options.negativePrompt,
      seed: options.seed,
    };

    const res = await fetch(`${this.config.sidecarBaseUrl}/images/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(`Image generation failed: HTTP ${res.status} - ${JSON.stringify(err)}`);
    }

    const data = (await res.json()) as { status: string; result: any };
    return {
      imageId: data.result.image_id,
      b64Data: data.result.b64_data,
      mimeType: data.result.mime_type,
      format: data.result.format,
      modelUsed: data.result.model_used,
      prompt: data.result.prompt,
      size: data.result.size,
      createdAt: data.result.created_at,
    };
  }
}
