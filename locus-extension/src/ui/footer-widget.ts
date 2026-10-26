/**
 * SPEC §7.1-7.9 / F-0030: Locus Footer Widget for Pi TUI.
 * Custom 3-column footer component hooked into Pi TUI footer slot.
 */
import { isEnabled } from "../config";

export interface FooterDashboardState {
  dcs: number;
  mode: string;
  active_faction: string;
  neo4j_nodes: number;
  neo4j_edges: number;
  livesync_status: string;
  sidecar_latency_ms: number;
  model_name: string;
}

export function formatThreeColumnRow(
  left: string,
  center: string,
  right: string,
  width: number = 80
): string {
  if (width < 30) {
    return `${left} | ${center} | ${right}`;
  }
  const totalLen = left.length + center.length + right.length;
  if (totalLen + 4 <= width) {
    const available = width - totalLen;
    const pad1 = Math.floor(available / 2);
    const pad2 = available - pad1;
    return `${left}${" ".repeat(pad1)}${center}${" ".repeat(pad2)}${right}`;
  }
  const maxCol = Math.max(10, Math.floor((width - 4) / 3));
  const lTrunc = left.slice(0, maxCol);
  const cTrunc = center.slice(0, maxCol);
  const rTrunc = right.slice(0, maxCol);
  const rem = width - (lTrunc.length + cTrunc.length + rTrunc.length);
  const p1 = Math.max(1, Math.floor(rem / 2));
  const p2 = Math.max(1, rem - p1);
  return `${lTrunc}${" ".repeat(p1)}${cTrunc}${" ".repeat(p2)}${rTrunc}`;
}

export class LocusFooterWidget {
  private latestState: FooterDashboardState = {
    dcs: 5.0,
    mode: "NORMAL",
    active_faction: "Leverage",
    neo4j_nodes: 0,
    neo4j_edges: 0,
    livesync_status: "OK",
    sidecar_latency_ms: 5,
    model_name: "claude-3-7-sonnet",
  };

  constructor(private readonly pollEndpoint: string = "http://localhost:8420/display/dashboard/state") {}

  public isEnabled(): boolean {
    return isEnabled("locus.tui_dashboard.enabled") && isEnabled("locus.tui.footer.enabled");
  }

  public updateState(state: Partial<FooterDashboardState>): void {
    this.latestState = { ...this.latestState, ...state };
  }

  public getState(): FooterDashboardState {
    return { ...this.latestState };
  }

  public render(width: number = 80): string {
    if (!this.isEnabled()) {
      return "";
    }
    const state = this.latestState;
    const leftCol = `DCS:${state.dcs.toFixed(1)} [${state.mode}] Faction:${state.active_faction}`;
    const centerCol = `Mem:${state.neo4j_nodes}n / ${state.neo4j_edges}e | LiveSync:${state.livesync_status}`;
    const rightCol = `Sidecar:${state.sidecar_latency_ms}ms | ${state.model_name}`;

    return formatThreeColumnRow(leftCol, centerCol, rightCol, width);
  }
}
