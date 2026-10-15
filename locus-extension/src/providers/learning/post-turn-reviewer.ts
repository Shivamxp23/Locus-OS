/**
 * Post-Turn Background Reviewer (§1.7 + §10.1)
 *
 * Dispatches asynchronous turn reflection for user preference extraction and skill curation.
 */

export const ALLOWED_REVIEW_TOOLS = new Set(["memory", "skill_manage"]);

export interface ReviewInsight {
  category: "preference" | "fact" | "skill";
  content: string;
  confidence: number;
}

export interface ReviewResult {
  session_id: string;
  turn_id: string;
  insights_extracted: ReviewInsight[];
  skills_updated: string[];
}

export class TurnReflector {
  private allowedTools = ALLOWED_REVIEW_TOOLS;

  public isToolAllowed(toolName: string): boolean {
    return this.allowedTools.has(toolName);
  }

  public extractInsights(messages: Array<{ content?: string }>): ReviewInsight[] {
    const insights: ReviewInsight[] = [];
    for (const msg of messages) {
      const text = String(msg.content || "");
      if (/i prefer|i always use|my project is|call me/i.test(text)) {
        insights.push({
          category: "preference",
          content: text.slice(0, 150),
          confidence: 0.90,
        });
      } else if (/new rule|remember to|convention/i.test(text)) {
        insights.push({
          category: "skill",
          content: text.slice(0, 150),
          confidence: 0.85,
        });
      }
    }
    return insights;
  }

  public reviewTurn(
    sessionId: string,
    turnId: string,
    messages: Array<{ content?: string }>
  ): ReviewResult {
    const insights = this.extractInsights(messages);
    return {
      session_id: sessionId,
      turn_id: turnId,
      insights_extracted: insights,
      skills_updated: insights.filter(i => i.category === "skill").map(i => i.content),
    };
  }
}
