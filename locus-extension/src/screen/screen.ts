/**
 * SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
 * Desktop Computer Use & Screen Client Contracts (F-0051 / US-79).
 *
 * Provides interfaces and client for screen capture, native desktop automation,
 * and vision-based screen intelligence element analysis.
 */

export interface ScreenElement {
  element_id: string;
  element_type: string;
  bbox: [number, number, number, number];
  center: [number, number];
  text: string;
  confidence: number;
  description: string;
  metadata?: Record<string, unknown>;
}

export interface DesktopAction {
  action_type:
    | "click"
    | "double_click"
    | "right_click"
    | "mouse_move"
    | "type"
    | "key_press"
    | "key_combination"
    | "screenshot"
    | "window_focus"
    | "scroll";
  x?: number;
  y?: number;
  text?: string;
  key?: string;
  keys?: string[];
  window_title?: string;
  delta_y?: number;
  metadata?: Record<string, unknown>;
}

export interface DesktopActionResult {
  status?: string;
  success: boolean;
  action_type: string;
  message: string;
  screenshot_base64?: string;
  details?: Record<string, unknown>;
  timestamp?: number;
}

export interface ScreenCaptureResult {
  status?: string;
  image_base64: string;
  width: number;
  height: number;
  format: string;
  display_id: number;
  window_title?: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface ScreenStatus {
  status: string;
  available: boolean;
  capture_backend: string;
  controller_backend: string;
  has_vision: boolean;
}

export class ScreenClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async captureScreen(options?: {
    display_id?: number;
    region?: [number, number, number, number];
    window_title?: string;
  }): Promise<ScreenCaptureResult> {
    const endpoint = `${this.baseUrl}/screen/capture`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options || {}),
    });
    if (resp.status === 503) {
      throw new Error("Screen capture is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to capture screen: ${resp.status}`);
    }
    return (await resp.json()) as ScreenCaptureResult;
  }

  async controlDesktop(action: DesktopAction): Promise<DesktopActionResult> {
    const endpoint = `${this.baseUrl}/screen/control`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(action),
    });
    if (resp.status === 503) {
      throw new Error("Desktop control is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to execute desktop action: ${resp.status}`);
    }
    return (await resp.json()) as DesktopActionResult;
  }

  async analyzeScreen(
    screenshotBase64?: string,
    prompt?: string
  ): Promise<{ status: string; elements: ScreenElement[]; count: number }> {
    const endpoint = `${this.baseUrl}/screen/analyze`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        screenshot: screenshotBase64,
        prompt,
      }),
    });
    if (resp.status === 503) {
      throw new Error("Screen intelligence is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to analyze screen: ${resp.status}`);
    }
    return (await resp.json()) as {
      status: string;
      elements: ScreenElement[];
      count: number;
    };
  }

  async executeWorkflow(
    actions: DesktopAction[]
  ): Promise<{ status: string; results: DesktopActionResult[]; count: number }> {
    const endpoint = `${this.baseUrl}/screen/execute`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actions }),
    });
    if (resp.status === 503) {
      throw new Error("Computer use workflow is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to execute computer use workflow: ${resp.status}`);
    }
    return (await resp.json()) as {
      status: string;
      results: DesktopActionResult[];
      count: number;
    };
  }

  async getStatus(): Promise<ScreenStatus> {
    const endpoint = `${this.baseUrl}/screen/status`;
    const resp = await fetch(endpoint, {
      method: "GET",
    });
    if (resp.status === 503) {
      throw new Error("Screen / Computer Use is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get screen status: ${resp.status}`);
    }
    return (await resp.json()) as ScreenStatus;
  }
}
