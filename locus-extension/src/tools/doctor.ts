/**
 * locus-extension/src/tools/doctor.ts - Doctor Diagnostics TypeScript client.
 *
 * Implements Spec §8.2
 */

export interface SystemCheckSummary {
  healthy: boolean;
  passedCount: number;
  failedCount: number;
}

export class DoctorClient {
  public evaluateSummary(passed: number, failed: number): SystemCheckSummary {
    return {
      healthy: failed === 0,
      passedCount: passed,
      failedCount: failed,
    };
  }
}
