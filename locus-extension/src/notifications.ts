/**
 * SPEC §29.4 lines 7531-7612: Notifications Client (F-0067 / US-105).
 * Source: OpenHuman notifications/dispatcher.py + Hermes gateway/platform_registry.py + Locus-original.
 */

export type NotificationPriority = "HIGH" | "MEDIUM" | "LOW";

export interface DeliveryResult {
  delivered: boolean;
  priority: NotificationPriority;
  reason?: string;
  queued?: boolean;
  channels?: string[];
  timestamp?: number;
}

export interface QueuedNotificationItem {
  id: string;
  message: string;
  priority: NotificationPriority;
  created_at: number;
  metadata?: Record<string, unknown>;
  delivered: boolean;
  delivery_timestamp?: number | null;
}

export interface QueueResponse {
  status: string;
  count: number;
  notifications: QueuedNotificationItem[];
}

export interface ProcessQueueResponse {
  status: string;
  processed: number;
  delivered: boolean;
  digest?: string;
  result?: DeliveryResult;
}

export interface NotificationClientConfig {
  sidecarBaseUrl?: string;
}

export class NotificationClient {
  private baseUrl: string;

  constructor(config: NotificationClientConfig = {}) {
    this.baseUrl = config.sidecarBaseUrl || "http://127.0.0.1:8420";
  }

  /**
   * SPEC §29.4: Send notification with priority and optional metadata.
   */
  async send(
    message: string,
    priority: NotificationPriority = "MEDIUM",
    metadata: Record<string, unknown> = {}
  ): Promise<DeliveryResult> {
    const res = await fetch(`${this.baseUrl}/notifications/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, priority, metadata }),
    });
    if (!res.ok) {
      throw new Error(`Send notification failed with HTTP ${res.status}`);
    }
    return (await res.json()) as DeliveryResult;
  }

  /**
   * SPEC §29.4: Retrieve list of buffered notifications.
   */
  async getQueue(): Promise<QueueResponse> {
    const res = await fetch(`${this.baseUrl}/notifications/queue`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Get notification queue failed with HTTP ${res.status}`);
    }
    return (await res.json()) as QueueResponse;
  }

  /**
   * SPEC §29.4: Flush and deliver summary digest of queued items.
   */
  async processQueue(): Promise<ProcessQueueResponse> {
    const res = await fetch(`${this.baseUrl}/notifications/process_queue`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Process notification queue failed with HTTP ${res.status}`);
    }
    return (await res.json()) as ProcessQueueResponse;
  }

  /**
   * Query status of notifications subsystem.
   */
  async getStatus(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.baseUrl}/notifications/status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Get notification status failed with HTTP ${res.status}`);
    }
    return (await res.json()) as Record<string, unknown>;
  }
}
