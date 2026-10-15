/**
 * Locus Vectorless Retrieval (PageIndex) Engine (§27.1) TypeScript companion.
 */

export interface PageIndexEntry {
  docId: string;
  sectionTitle: string;
  level: number;
  startChar: number;
  endChar: number;
  summary: string;
  keywords: string[];
}

export class PageIndexEngine {
  private entries: Map<string, PageIndexEntry[]> = new Map();

  indexMarkdown(docId: string, markdownText: string): PageIndexEntry[] {
    const lines = markdownText.split(/\r?\n/);
    const result: PageIndexEntry[] = [];
    let charOffset = 0;

    let currentHeader: string | null = null;
    let currentLevel = 1;
    let currentStart = 0;
    let currentBodyLines: string[] = [];

    const headerRegex = /^(#{1,6})\s+(.*)$/;

    for (const line of lines) {
      const lineLen = line.length + 1;
      const match = headerRegex.exec(line);
      if (match) {
        if (currentHeader !== null) {
          const summary = currentBodyLines.join(' ').slice(0, 120);
          const words = Array.from(new Set(summary.toLowerCase().match(/\b\w{3,}\b/g) || [])).slice(0, 10);
          result.push({
            docId,
            sectionTitle: currentHeader,
            level: currentLevel,
            startChar: currentStart,
            endChar: charOffset,
            summary,
            keywords: words,
          });
        }
        currentLevel = match[1].length;
        currentHeader = match[2].trim();
        currentStart = charOffset;
        currentBodyLines = [];
      } else {
        currentBodyLines.push(line);
      }
      charOffset += lineLen;
    }

    if (currentHeader !== null) {
      const summary = currentBodyLines.join(' ').slice(0, 120);
      const words = Array.from(new Set(summary.toLowerCase().match(/\b\w{3,}\b/g) || [])).slice(0, 10);
      result.push({
        docId,
        sectionTitle: currentHeader,
        level: currentLevel,
        startChar: currentStart,
        endChar: charOffset,
        summary,
        keywords: words,
      });
    }

    this.entries.set(docId, result);
    return result;
  }

  searchIndex(query: string, limit: number = 5): PageIndexEntry[] {
    const queryWords = new Set(query.toLowerCase().split(/\s+/));
    const scored: Array<{ score: number; entry: PageIndexEntry }> = [];

    for (const list of this.entries.values()) {
      for (const e of list) {
        let score = 0;
        const titleWords = new Set(e.sectionTitle.toLowerCase().split(/\s+/));
        for (const qw of queryWords) {
          if (titleWords.has(qw)) score += 3.0;
          if (e.keywords.includes(qw)) score += 1.5;
        }
        if (e.summary.toLowerCase().includes(query.toLowerCase())) score += 2.0;

        if (score > 0) {
          scored.push({ score, entry: e });
        }
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, limit).map((s) => s.entry);
  }
}
