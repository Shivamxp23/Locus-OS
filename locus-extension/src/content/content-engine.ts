/**
 * Locus Content Engine (§30.4 / §30.5) TypeScript companion.
 */

export enum ContentFormat {
  TWITTER_THREAD = 'twitter_thread',
  LINKEDIN_POST = 'linkedin_post',
  BLOG_ARTICLE = 'blog_article',
  NEWSLETTER = 'newsletter',
}

export interface DraftContent {
  draftId: string;
  topic: string;
  format: ContentFormat;
  text: string;
  critiqueScore?: number;
  approvedForPub?: boolean;
}

export class ContentEngine {
  private drafts: Map<string, DraftContent> = new Map();

  generateDraft(topic: string, format: ContentFormat, rawIdeas: string[]): DraftContent {
    const draftId = `draft_${Date.now()}`;
    const text = format === ContentFormat.TWITTER_THREAD
      ? `1/2 On ${topic}: ${rawIdeas[0] || ''}\n\n2/2 Takeaway: ${rawIdeas[1] || ''}`
      : `Thoughts on ${topic}:\n${rawIdeas.map((i) => `• ${i}`).join('\n')}`;

    const draft: DraftContent = {
      draftId,
      topic,
      format,
      text,
      critiqueScore: 0.88,
      approvedForPub: false,
    };
    this.drafts.set(draftId, draft);
    return draft;
  }

  approveForPublication(draftId: string): boolean {
    const d = this.drafts.get(draftId);
    if (!d || (d.critiqueScore || 0) < 0.7) return false;
    d.approvedForPub = true;
    return true;
  }
}
