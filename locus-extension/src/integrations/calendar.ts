/**
 * SPEC §21.1-21.3 lines 6624-6678: Google Calendar, Gmail, Webhooks.
 * Extension client for calendar events, temporal scheduling, and webhooks.
 */

export interface CalendarEvent {
  id: string;
  summary: string;
  start_time: string;
  end_time: string;
  description?: string;
  location?: string;
  html_link?: string;
  attendees?: string[];
}

export interface CalendarAuthResponse {
  status: string;
  auth_url?: string;
  authenticated?: boolean;
  tokens?: Record<string, unknown>;
  redirect_uri?: string;
}

export interface WebhookRegistration {
  id: string;
  url: string;
  events: string[];
  secret: string;
  created_at: number;
}

export class CalendarSyncClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async getAuthUrl(redirect_uri = "urn:ietf:wg:oauth:2.0:oob"): Promise<CalendarAuthResponse> {
    const res = await fetch(`${this.baseUrl}/integrations/calendar/auth-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ redirect_uri }),
    });
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async exchangeCode(code: string, redirect_uri = "urn:ietf:wg:oauth:2.0:oob"): Promise<CalendarAuthResponse> {
    const res = await fetch(`${this.baseUrl}/integrations/calendar/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, redirect_uri }),
    });
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async listEvents(time_min?: string, time_max?: string): Promise<{ status: string; events: CalendarEvent[]; count: number }> {
    const params = new URLSearchParams();
    if (time_min) params.set("time_min", time_min);
    if (time_max) params.set("time_max", time_max);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${this.baseUrl}/integrations/calendar/events${qs}`);
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async createEvent(event: Omit<CalendarEvent, "id">): Promise<{ status: string; event: CalendarEvent }> {
    const res = await fetch(`${this.baseUrl}/integrations/calendar/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(event),
    });
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async getTemporalContext(): Promise<{ status: string; temporal_context: string }> {
    const res = await fetch(`${this.baseUrl}/integrations/calendar/temporal`);
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async registerWebhook(url: string, events: string[], secret?: string): Promise<{ status: string; webhook: WebhookRegistration }> {
    const res = await fetch(`${this.baseUrl}/integrations/webhooks/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, events, secret }),
    });
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }

  async fireWebhook(event_type: string, payload: Record<string, unknown>): Promise<{ status: string; dispatches: unknown[] }> {
    const res = await fetch(`${this.baseUrl}/integrations/webhooks/fire`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type, payload }),
    });
    if (res.status === 503) {
      throw new Error("Calendar integration is disabled (HTTP 503)");
    }
    return res.json();
  }
}
