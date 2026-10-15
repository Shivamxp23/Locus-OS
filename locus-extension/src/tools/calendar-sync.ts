/**
 * locus-extension/src/tools/calendar-sync.ts - Calendar Sync TypeScript client.
 *
 * Implements Spec §21.1-21.3
 */

export interface CalendarEventPayload {
  id: string;
  title: string;
  startTime: string;
  endTime: string;
}

export class CalendarSyncClient {
  public formatEventSummary(event: CalendarEventPayload): string {
    return `[${event.startTime} - ${event.endTime}] ${event.title}`;
  }
}
