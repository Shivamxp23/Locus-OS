/**
 * Locus Skill System & Multi-Source Marketplace (§10.7 / §9.2) TypeScript companion.
 */

export interface SkillManifest {
  name: string;
  description: string;
  version: string;
  source: string;
  tools: string[];
  permissions?: string[];
  isInstalled: boolean;
}

export class SkillMarketplaceManager {
  private availableSkills: Map<string, SkillManifest> = new Map();
  private installedSkills: Map<string, SkillManifest> = new Map();

  constructor() {
    this.addCatalogSkill({
      name: 'alphafold-database',
      description: 'Retrieve AlphaFold 3D structures and confidence metrics',
      version: '1.2.0',
      source: 'builtin',
      tools: ['fetch_pdb', 'analyze_plddt'],
      isInstalled: true,
    });
    this.addCatalogSkill({
      name: 'excalidraw-builder',
      description: 'Generates native Excalidraw diagram JSON structures',
      version: '2.0.1',
      source: 'marketplace',
      tools: ['build_excalidraw_diagram'],
      isInstalled: true,
    });
  }

  private addCatalogSkill(skill: SkillManifest) {
    this.availableSkills.set(skill.name, skill);
    if (skill.isInstalled) {
      this.installedSkills.set(skill.name, skill);
    }
  }

  searchSkills(query: string): SkillManifest[] {
    const q = query.toLowerCase();
    return Array.from(this.availableSkills.values()).filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q)
    );
  }

  installSkill(skillName: string): boolean {
    const s = this.availableSkills.get(skillName);
    if (!s) return false;
    s.isInstalled = true;
    this.installedSkills.set(skillName, s);
    return true;
  }
}
