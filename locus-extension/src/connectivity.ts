/**
 * locus-extension/src/connectivity.ts - Connectivity Checker TypeScript client.
 *
 * Implements Spec §29.5
 */

export interface ProbeResult {
  target: string;
  isReachable: boolean;
  latencyMs: number;
}

export class ConnectivityClient {
  public isOnline(probe: ProbeResult): boolean {
    return probe.isReachable;
  }
}
