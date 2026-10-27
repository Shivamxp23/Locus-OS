/**
 * SPEC §25.13: TypeScript client for Review Cadence System.
 */

export interface ReviewPromptData {
  cadence: string;
  title: string;
  schedule: string;
  model: string;
  sections: string[];
  context_data: Record<string, unknown>;
}

export interface ReviewResultData {
  cadence: string;
  prompt: ReviewPromptData;
  content: string;
  generated_at: string;
  status: string;
}

export interface ScheduledCadenceData {
  cadence: string;
  title: string;
  schedule: string;
  model: string;
  enabled: boolean;
  disabled_by: string | null;
}

export interface ReviewsClientOptions {
  sidecarUrl?: string;
}

export class ReviewCadenceClient {
  private readonly baseUrl: string;

  constructor(options: ReviewsClientOptions = {}) {
    this.baseUrl = options.sidecarUrl || "http://127.0.0.1:8420";
  }

  async generateReview(
    cadence: string,
    context?: Record<string, unknown>
  ): Promise<{
    status: string;
    review: ReviewResultData;
  }> {
    const res = await fetch(`${this.baseUrl}/reviews/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cadence,
        context,
      }),
    });
    if (!res.ok) {
      throw new Error(`Failed to generate review: ${res.status}`);
    }
    return res.json();
  }

  async listScheduledReviews(): Promise<{
    status: string;
    cadences: ScheduledCadenceData[];
  }> {
    const res = await fetch(`${this.baseUrl}/reviews/scheduled`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to list scheduled reviews: ${res.status}`);
    }
    return res.json();
  }

  async getStatus(): Promise<{
    status: string;
    provider: string;
    enabled: boolean;
    cadences: string[];
    defaults: Record<string, Record<string, string>>;
  }> {
    const res = await fetch(`${this.baseUrl}/reviews/status`, {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to get review status: ${res.status}`);
    }
    return res.json();
  }
}
