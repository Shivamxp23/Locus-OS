/**
 * locus-extension/src/life-os/scheduler.ts - Deterministic 6-Step Scheduler (TS definition).
 *
 * Implements Spec §25.12
 */

import { Faction, GoalTask } from "./goal-stack";

export enum OperatingMode {
  SURVIVAL = "SURVIVAL",
  RECOVERY = "RECOVERY",
  NORMAL = "NORMAL",
  DEEP_WORK = "DEEP_WORK",
  PEAK = "PEAK",
}

export function resolveOperatingMode(dcs: number): OperatingMode {
  if (dcs <= 2.0) return OperatingMode.SURVIVAL;
  if (dcs <= 4.0) return OperatingMode.RECOVERY;
  if (dcs <= 6.0) return OperatingMode.NORMAL;
  if (dcs <= 8.0) return OperatingMode.DEEP_WORK;
  return OperatingMode.PEAK;
}

export function calculateSchedulerTws(
  difficulty: number,
  leverage: number,
  urgency: number,
  consequence: number,
  deferralCount: number = 0,
): number {
  const d = Math.max(1, Math.min(10, difficulty));
  const l = Math.max(1, Math.min(10, leverage));
  const u = Math.max(1, Math.min(10, urgency));
  const c = Math.max(1, Math.min(10, consequence));
  const base = (d * 0.35) + (l * 0.25) + (u * 0.20) + (c * 0.20);
  const deferralBonus = Math.min(2.5, deferralCount * 0.5);
  return Number((base + deferralBonus).toFixed(2));
}
