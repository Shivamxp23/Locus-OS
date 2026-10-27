/**
 * SPEC §28.1-28.6 lines 7380-7432:
 * Dual Interface, 4 Daily Check-ins, and Zero-Cost Budget Guard TypeScript Client (F-0064 / US-101).
 *
 * Interfaces and client for unified session routing between TUI and Telegram,
 * inline keyboard layout generation, structured daily check-ins with DCS scoring,
 * and cost tracking against daily budget.
 */

export interface SessionMessage {
  channel: string;
  session_id: string;
  content: string;
  sender: string;
  timestamp: string;
}

export interface RouteMessageParams {
  channel: string;
  sessionId: string;
  content: string;
  sender?: string;
}

export interface RouteMessageResult {
  status: string;
  session_id?: string;
  channel?: string;
  message?: SessionMessage;
  total_messages?: number;
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface InlineKeyboardButton {
  text: string;
  callback_data: string;
}

export interface CheckInKeyboardResult {
  slot: string;
  keyboard: InlineKeyboardButton[][];
  status_code: number;
  error?: string;
  disabled?: string;
}

export interface CheckInRecord {
  slot: string;
  energy: number;
  stress: number;
  mood: number;
  readiness: string;
  notes: string;
  dcs_score: number;
  operating_mode: string;
  timestamp: string;
  status_code?: number;
  error?: string;
  disabled?: string;
}

export interface SubmitCheckinParams {
  slot: string;
  energy?: number;
  stress?: number;
  mood?: number;
  readiness?: string;
  notes?: string;
}

export interface CostBudgetResult {
  daily_tokens: number;
  daily_cost_usd: number;
  daily_budget_usd: number;
  budget_usage_pct: number;
  skip_inner_loop_recommended: boolean;
  default_model: string;
  status_code?: number;
  error?: string;
  disabled?: string;
}

export interface DualInterfaceStatusResult {
  subsystem_enabled: boolean;
  active_sessions_count: number;
  total_checkins_count: number;
  budget: CostBudgetResult;
  provider_enabled: boolean;
  provider_name: string;
  status_code: number;
  error?: string;
  disabled?: string;
}

export class DualInterfaceClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async routeMessage(params: RouteMessageParams): Promise<RouteMessageResult> {
    const res = await fetch(`${this.baseUrl}/gateway/interface/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: params.channel,
        session_id: params.sessionId,
        content: params.content,
        sender: params.sender || "user",
      }),
    });
    return (await res.json()) as RouteMessageResult;
  }

  async getCheckinKeyboard(slot: string = "07:30_MORNING"): Promise<CheckInKeyboardResult> {
    const res = await fetch(`${this.baseUrl}/gateway/checkin/keyboard?slot=${encodeURIComponent(slot)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as CheckInKeyboardResult;
  }

  async submitCheckin(params: SubmitCheckinParams): Promise<CheckInRecord> {
    const res = await fetch(`${this.baseUrl}/gateway/checkin/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        slot: params.slot,
        energy: params.energy ?? 7.0,
        stress: params.stress ?? 3.0,
        mood: params.mood ?? 0.5,
        readiness: params.readiness ?? "Ready to go!",
        notes: params.notes ?? "",
      }),
    });
    return (await res.json()) as CheckInRecord;
  }

  async getCostBudget(): Promise<CostBudgetResult> {
    const res = await fetch(`${this.baseUrl}/gateway/cost/budget`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as CostBudgetResult;
  }

  async getStatus(): Promise<DualInterfaceStatusResult> {
    const res = await fetch(`${this.baseUrl}/gateway/interface/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    return (await res.json()) as DualInterfaceStatusResult;
  }
}
