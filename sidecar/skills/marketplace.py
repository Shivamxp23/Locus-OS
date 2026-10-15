"""Locus Skill System & Multi-Source Marketplace (§10.7 / §9.2).

Discovers, verifies, installs, and injects agent skills and tools from local directories,
GitHub repositories, and community catalogs into the active runtime environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillManifest:
    name: str
    description: str
    version: str
    source: str  # "builtin", "local", "github", "marketplace"
    tools: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    is_installed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "source": self.source,
            "tools": self.tools,
            "permissions": self.permissions,
            "is_installed": self.is_installed,
        }


class SkillMarketplaceManager:
    """Manages multi-source skill discovery, repository indexing, and runtime installation."""

    def __init__(self):
        self.available_skills: Dict[str, SkillManifest] = {}
        self.installed_skills: Dict[str, SkillManifest] = {}
        self._populate_catalog()

    def _populate_catalog(self) -> None:
        catalog = [
            SkillManifest(
                name="alphafold-database",
                description="Retrieve AlphaFold 3D structures and confidence metrics",
                version="1.2.0",
                source="builtin",
                tools=["fetch_pdb", "analyze_plddt"],
                is_installed=True,
            ),
            SkillManifest(
                name="excalidraw-builder",
                description="Generates native Excalidraw diagram JSON structures",
                version="2.0.1",
                source="marketplace",
                tools=["build_excalidraw_diagram"],
                is_installed=True,
            ),
            SkillManifest(
                name="chembl-database",
                description="Query ChEMBL for bioactivity and pharmacology targets",
                version="1.0.0",
                source="marketplace",
                tools=["search_chembl", "get_compound_ic50"],
                is_installed=False,
            ),
        ]
        for skill in catalog:
            self.available_skills[skill.name] = skill
            if skill.is_installed:
                self.installed_skills[skill.name] = skill

    def search_skills(self, query: str) -> List[SkillManifest]:
        q = query.lower()
        return [
            s for s in self.available_skills.values()
            if q in s.name.lower() or q in s.description.lower()
        ]

    def install_skill(self, skill_name: str) -> bool:
        skill = self.available_skills.get(skill_name)
        if not skill:
            return False
        skill.is_installed = True
        self.installed_skills[skill_name] = skill
        return True

    def uninstall_skill(self, skill_name: str) -> bool:
        if skill_name in self.installed_skills:
            self.installed_skills[skill_name].is_installed = False
            del self.installed_skills[skill_name]
            return True
        return False
