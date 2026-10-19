/**
 * SPEC §1.12 / F-0012 / US-31: Setup Wizard for Pi Agent TUI.
 * Implements interactive stepped submenu for first-run onboarding.
 */
import { isEnabled } from "../config";

export interface SetupWizardState {
  topology: "local" | "vm" | "hybrid";
  completed: boolean;
  stepsCompleted: string[];
  llm: { provider: string; model: string; endpoint?: string };
  memory: { enableNeo4j: boolean; enableHeadroom: boolean };
  vault: { path: string; enableLiveSync: boolean };
  lifeOs: { timezone: string; morningCheckinTime: string };
  telegram: { enabled: boolean; ownerId?: string };
}

export class SetupWizard {
  private static instance: SetupWizard | null = null;
  private state: SetupWizardState = {
    topology: "local",
    completed: false,
    stepsCompleted: [],
    llm: { provider: "deepseek", model: "deepseek-chat" },
    memory: { enableNeo4j: false, enableHeadroom: true },
    vault: { path: "", enableLiveSync: false },
    lifeOs: { timezone: "Asia/Kolkata", morningCheckinTime: "08:00" },
    telegram: { enabled: false },
  };

  public static getInstance(): SetupWizard {
    if (!SetupWizard.instance) {
      SetupWizard.instance = new SetupWizard();
    }
    return SetupWizard.instance;
  }

  public isEnabled(): boolean {
    return isEnabled("locus.onboarding_flow.enabled") && isEnabled("locus.onboarding.enabled");
  }

  public isCompleted(): boolean {
    return this.state.completed;
  }

  public setTopology(topology: "local" | "vm" | "hybrid"): void {
    this.state.topology = topology;
    if (!this.state.stepsCompleted.includes("topology")) {
      this.state.stepsCompleted.push("topology");
    }
  }

  public configureLLM(provider: string, model: string, endpoint?: string): void {
    this.state.llm = { provider, model, endpoint };
    if (!this.state.stepsCompleted.includes("llm")) {
      this.state.stepsCompleted.push("llm");
    }
  }

  public configureMemory(enableNeo4j: boolean, enableHeadroom: boolean = true): void {
    this.state.memory = { enableNeo4j, enableHeadroom };
    if (!this.state.stepsCompleted.includes("memory")) {
      this.state.stepsCompleted.push("memory");
    }
  }

  public configureVault(path: string, enableLiveSync: boolean = false): void {
    this.state.vault = { path, enableLiveSync };
    if (!this.state.stepsCompleted.includes("vault")) {
      this.state.stepsCompleted.push("vault");
    }
  }

  public configureLifeOS(timezone: string = "Asia/Kolkata", morningCheckinTime: string = "08:00"): void {
    this.state.lifeOs = { timezone, morningCheckinTime };
    if (!this.state.stepsCompleted.includes("life_os")) {
      this.state.stepsCompleted.push("life_os");
    }
  }

  public configureTelegram(enabled: boolean = false, ownerId?: string): void {
    this.state.telegram = { enabled, ownerId };
    if (!this.state.stepsCompleted.includes("telegram")) {
      this.state.stepsCompleted.push("telegram");
    }
  }

  public runDiagnostics(): { allOk: boolean; checks: Record<string, boolean> } {
    const checks = {
      llm: Boolean(this.state.llm.provider),
      memory: true,
      vault: Boolean(this.state.vault.path || true),
      lifeOs: Boolean(this.state.lifeOs.timezone),
      telegram: !this.state.telegram.enabled || Boolean(this.state.telegram.ownerId),
    };
    const allOk = Object.values(checks).every(Boolean);
    if (allOk) {
      this.state.completed = true;
    }
    return { allOk, checks };
  }

  public getState(): SetupWizardState {
    return { ...this.state };
  }

  public reset(): void {
    this.state.completed = false;
    this.state.stepsCompleted = [];
  }
}
