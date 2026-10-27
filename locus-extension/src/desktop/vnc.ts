/**
 * SPEC §20.3 lines 6555-6621: VNC / Remote Desktop Protocol Control.
 * Client library for interacting with sidecar VNC service and bounding box security.
 */

export interface BoundingBox {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export function createBoundingBox(
  min_x = 0,
  min_y = 0,
  max_x = 1920,
  max_y = 1080
): BoundingBox {
  return { min_x, min_y, max_x, max_y };
}

export function containsCoordinate(box: BoundingBox, x: number, y: number): boolean {
  return x >= box.min_x && x <= box.max_x && y >= box.min_y && y <= box.max_y;
}

export interface VNCActionResult {
  status: string;
  action?: string;
  coordinates?: { x: number; y: number };
  button?: string;
  trajectory_steps?: number;
  characters_count?: number;
  error?: string;
  disabled?: string;
}

export interface VNCFrameResult {
  format: string;
  data: string;
  width: number;
  height: number;
  timestamp: number;
}

export interface VNCStatusResult {
  host: string;
  port: number;
  connected: boolean;
  current_pos: [number, number];
  safety_boundary: BoundingBox;
}

export class VNCClient {
  constructor(private readonly baseUrl: string = "http://127.0.0.1:8420") {}

  async connect(host = "127.0.0.1", port = 5900, password = ""): Promise<{ status: string; connected: boolean }> {
    const res = await fetch(`${this.baseUrl}/vnc/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ host, port, password }),
    });
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    return res.json();
  }

  async disconnect(): Promise<{ status: string; connected: boolean }> {
    const res = await fetch(`${this.baseUrl}/vnc/disconnect`, {
      method: "POST",
    });
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    return res.json();
  }

  async captureFramebuffer(): Promise<VNCFrameResult> {
    const res = await fetch(`${this.baseUrl}/vnc/capture`);
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    return res.json();
  }

  async click(x: number, y: number, button = "left", steps = 5): Promise<VNCActionResult> {
    const res = await fetch(`${this.baseUrl}/vnc/click`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x, y, button, steps }),
    });
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    if (res.status === 403) {
      const err = await res.json();
      throw new Error(`Security Violation: ${err.message || "Out of bounds"}`);
    }
    return res.json();
  }

  async typeKeys(text: string): Promise<VNCActionResult> {
    const res = await fetch(`${this.baseUrl}/vnc/type`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    return res.json();
  }

  async getStatus(): Promise<VNCStatusResult> {
    const res = await fetch(`${this.baseUrl}/vnc/status`);
    if (res.status === 503) {
      throw new Error("VNC remote control is disabled (HTTP 503)");
    }
    return res.json();
  }
}
