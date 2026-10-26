/**
 * SPEC §7.1-7.9 / F-0030: Settings Selector Component for Pi TUI.
 * Provides interactive modal configuration for Locus subsystems.
 */
import { get, isEnabled } from "../config";

export interface SettingItem {
  key: string;
  label: string;
  value: string;
}

export class LocusSettingsSelector {
  private items: SettingItem[] = [];

  constructor() {
    this.refreshItems();
  }

  public isEnabled(): boolean {
    return isEnabled("locus.tui_dashboard.enabled") && isEnabled("locus.tui.settings.enabled");
  }

  public refreshItems(): void {
    this.items = [
      { key: "locus.topology", label: "Deployment Topology", value: String(get("locus.topology", "local")) },
      { key: "locus.providers.llm.provider", label: "Primary LLM Provider", value: String(get("locus.providers.llm.provider", "anthropic")) },
      { key: "locus.providers.memory.enabled", label: "Neo4j Agent Memory", value: isEnabled("locus.providers.memory.enabled") ? "ENABLED" : "DISABLED" },
      { key: "locus.providers.compression.enabled", label: "Headroom Compression", value: isEnabled("locus.providers.compression.enabled") ? "ENABLED" : "DISABLED" },
      { key: "locus.providers.vault_sync.enabled", label: "CouchDB LiveSync", value: isEnabled("locus.providers.vault_sync.enabled") ? "ACTIVE" : "OFF" },
      { key: "locus.cron.enabled", label: "Proactive Inner Loop", value: isEnabled("locus.cron.enabled") ? "90-MIN CRON" : "OFF" },
      { key: "locus.providers.channels.telegram.enabled", label: "Telegram Gateway", value: isEnabled("locus.providers.channels.telegram.enabled") ? "CONNECTED" : "OFF" },
    ];
  }

  public getItems(): SettingItem[] {
    return [...this.items];
  }
}
