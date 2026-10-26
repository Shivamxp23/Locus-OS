/**
 * SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
 * Browser Automation Client & TypeScript Contracts (F-0045 / US-78).
 *
 * Interfaces and client for browser automation, screen intelligence, and
 * automated page navigation/interaction workflows.
 */

export interface UIElement {
  id: string;
  tag: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  interactive: boolean;
  selector?: string;
}

export interface BrowserAction {
  type: "click" | "type" | "navigate";
  selector?: string;
  text?: string;
  x?: number;
  y?: number;
}

export interface BrowserTask {
  url: string;
  actions?: BrowserAction[];
  capture_screenshot?: boolean;
}

export interface BrowserResult {
  status: string;
  url: string;
  title: string;
  content: string;
  screenshot_base64?: string;
  elements?: UIElement[];
  logs?: string[];
}

export interface BrowserEnginesInfo {
  status: string;
  engines: string[];
  active_engine: string;
}

export class BrowserClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async navigate(url: string): Promise<BrowserResult> {
    const endpoint = `${this.baseUrl}/browser/navigate`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to navigate browser: ${resp.status}`);
    }
    return (await resp.json()) as BrowserResult;
  }

  async click(selector?: string, x?: number, y?: number): Promise<BrowserResult> {
    const endpoint = `${this.baseUrl}/browser/click`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selector, x, y }),
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to click element: ${resp.status}`);
    }
    return (await resp.json()) as BrowserResult;
  }

  async typeText(text: string, selector?: string): Promise<BrowserResult> {
    const endpoint = `${this.baseUrl}/browser/type`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, selector }),
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to type text: ${resp.status}`);
    }
    return (await resp.json()) as BrowserResult;
  }

  async screenshot(): Promise<{ screenshot: string; format: string }> {
    const endpoint = `${this.baseUrl}/browser/screenshot`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { Accept: "application/json" },
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to capture screenshot: ${resp.status}`);
    }
    return (await resp.json()) as { status: string; screenshot: string; format: string };
  }

  async analyzeScreen(screenshotBase64?: string): Promise<UIElement[]> {
    const endpoint = `${this.baseUrl}/browser/analyze`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screenshot: screenshotBase64 }),
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to analyze screen: ${resp.status}`);
    }
    const data = (await resp.json()) as { status: string; elements: UIElement[] };
    return data.elements || [];
  }

  async automateTask(task: BrowserTask): Promise<BrowserResult> {
    const endpoint = `${this.baseUrl}/browser/automate`;
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(task),
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to automate task: ${resp.status}`);
    }
    return (await resp.json()) as BrowserResult;
  }

  async getProviders(): Promise<BrowserEnginesInfo> {
    const endpoint = `${this.baseUrl}/browser/providers`;
    const resp = await fetch(endpoint, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (resp.status === 503) {
      throw new Error("Browser automation is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get browser providers: ${resp.status}`);
    }
    return (await resp.json()) as BrowserEnginesInfo;
  }
}
