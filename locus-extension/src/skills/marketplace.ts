/**
 * SPEC §9.2: Skill System & Multi-Source Marketplace (F-0119 / US-63).
 * TypeScript client contract for multi-source skill discovery and installation.
 */

export interface SkillManifest {
  name: string;
  description: string;
  version: string;
  author: string;
  repository_url: string;
  dependencies: string[];
  env_vars_required: string[];
  bundle_url?: string;
}

export interface SkillInstallResult {
  success: boolean;
  source: string;
  skill_name: string;
  manifest: SkillManifest;
  prerequisites: {
    valid: boolean;
    missing_env_vars: string[];
    required_count: number;
  };
}

export class SkillMarketplaceClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8420") {
    this.baseUrl = baseUrl;
  }

  async getSources(): Promise<Record<string, string>> {
    const res = await fetch(`${this.baseUrl}/skills/marketplace/sources`);
    if (!res.ok) {
      throw new Error(`Failed to fetch marketplace sources: ${res.statusText}`);
    }
    const data = await res.json();
    return data.sources;
  }

  async getManifest(source: string, skillName: string): Promise<SkillManifest> {
    const res = await fetch(
      `${this.baseUrl}/skills/marketplace/manifest?source=${encodeURIComponent(source)}&skill_name=${encodeURIComponent(skillName)}`
    );
    if (!res.ok) {
      throw new Error(`Failed to fetch manifest: ${res.statusText}`);
    }
    const data = await res.json();
    return data.manifest;
  }

  async installSkill(source: string, skillName: string): Promise<SkillInstallResult> {
    const res = await fetch(`${this.baseUrl}/skills/marketplace/install`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, skill_name: skillName }),
    });
    if (!res.ok) {
      throw new Error(`Failed to install skill: ${res.statusText}`);
    }
    return await res.json();
  }

  async listInstalled(): Promise<SkillManifest[]> {
    const res = await fetch(`${this.baseUrl}/skills/marketplace/installed`);
    if (!res.ok) {
      throw new Error(`Failed to list installed skills: ${res.statusText}`);
    }
    const data = await res.json();
    return data.installed;
  }
}
