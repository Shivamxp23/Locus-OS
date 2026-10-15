/**
 * Locus Spaced Repetition Engine (§30.5 / §30.6) TypeScript companion.
 */

export interface SpacedRepetitionCard {
  cardId: string;
  frontPrompt: string;
  backAnswer: string;
  repetitions: number;
  intervalDays: number;
  easeFactor: number;
  nextReviewTimestamp: number;
  tags?: string[];
}

export class SpacedRepetitionEngine {
  private cards: Map<string, SpacedRepetitionCard> = new Map();

  addCard(cardId: string, front: string, back: string, tags?: string[]): SpacedRepetitionCard {
    const card: SpacedRepetitionCard = {
      cardId,
      frontPrompt: front,
      backAnswer: back,
      repetitions: 0,
      intervalDays: 1,
      easeFactor: 2.5,
      nextReviewTimestamp: Date.now(),
      tags: tags || [],
    };
    this.cards.set(cardId, card);
    return card;
  }

  reviewCard(cardId: string, quality: number): SpacedRepetitionCard {
    const card = this.cards.get(cardId)!;
    const q = Math.max(0, Math.min(5, quality));

    if (q >= 3) {
      if (card.repetitions === 0) card.intervalDays = 1;
      else if (card.repetitions === 1) card.intervalDays = 6;
      else card.intervalDays = Math.round(card.intervalDays * card.easeFactor);
      card.repetitions++;
    } else {
      card.repetitions = 0;
      card.intervalDays = 1;
    }

    card.easeFactor = Math.max(1.3, card.easeFactor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)));
    card.nextReviewTimestamp = Date.now() + card.intervalDays * 86400 * 1000;
    return card;
  }
}
