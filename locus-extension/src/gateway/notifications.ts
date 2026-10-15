/**
 * Locus Notification Dispatcher (§29.4) TypeScript companion.
 */

export enum NotificationPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface NotificationPayload {
  title: string;
  body: string;
  priority?: NotificationPriority;
  category?: string;
  timestamp?: number;
  metadata?: Record<string, any>;
  channels?: string[];
}

export class NotificationDispatcher {
  private throttleWindowMs: number;
  private lastDispatch: Map<string, number> = new Map();
  private history: NotificationPayload[] = [];

  constructor(throttleWindowSeconds: number = 2.0) {
    this.throttleWindowMs = throttleWindowSeconds * 1000;
  }

  dispatch(payload: NotificationPayload): Record<string, boolean> {
    const priority = payload.priority || NotificationPriority.NORMAL;
    const category = payload.category || 'general';
    const channels = payload.channels || ['desktop', 'telegram'];
    const now = Date.now();

    if (priority !== NotificationPriority.URGENT) {
      const last = this.lastDispatch.get(category) || 0;
      if (now - last < this.throttleWindowMs) {
        return { throttled: true };
      }
    }

    this.lastDispatch.set(category, now);
    this.history.push({
      ...payload,
      priority,
      category,
      channels,
      timestamp: payload.timestamp || now,
    });

    const results: Record<string, boolean> = {};
    for (const ch of channels) {
      results[ch] = true;
    }
    return results;
  }

  getRecentNotifications(limit: number = 20): NotificationPayload[] {
    return this.history.slice(-limit);
  }
}
