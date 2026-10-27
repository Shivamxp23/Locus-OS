"""
SPEC §27.4 lines 7152-7191: 3-Level Tag Hierarchy & Semantic Indexing (F-0123 / US-97).
Source: Comprehensive Locus System Design.html
Logic:
    Enforces strict 3-level domain/category/instance tag taxonomy across vault notes:
    - Level 1: Domain (#domain/health, #domain/craft, #domain/leverage, #domain/expression)
    - Level 2: Category (#category/exercise, #category/coding, #category/writing)
    - Level 3: Instance (#instance/locus-os, #instance/deepseek, #instance/2026-08)
    Or 3-part hierarchy: #domain/category/instance (e.g. #craft/coding/locus-os).
    Auto-resolves bare tags to domain hierarchy via category-to-domain taxonomy map.
Off state:
    locus.vault.tag_manager.enabled: when off, tags are returned unnormalized.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar import config

logger = logging.getLogger("locus.vault.tag_manager")

VALID_DOMAINS: Set[str] = {
    "health",
    "craft",
    "leverage",
    "expression",
}

DEFAULT_CATEGORY_TO_DOMAIN: Dict[str, str] = {
    # Health
    "exercise": "health",
    "sleep": "health",
    "nutrition": "health",
    "workout": "health",
    "cardio": "health",
    "mental_health": "health",
    "recovery": "health",
    "fitness": "health",
    # Craft
    "coding": "craft",
    "engineering": "craft",
    "architecture": "craft",
    "design": "craft",
    "writing": "craft",
    "research": "craft",
    "python": "craft",
    "typescript": "craft",
    "software": "craft",
    # Leverage
    "business": "leverage",
    "finance": "leverage",
    "money": "leverage",
    "career": "leverage",
    "sales": "leverage",
    "investing": "leverage",
    "strategy": "leverage",
    "client": "leverage",
    # Expression
    "content": "expression",
    "art": "expression",
    "video": "expression",
    "podcast": "expression",
    "photography": "expression",
    "youtube": "expression",
    "creative": "expression",
}


@dataclass
class TagValidationResult:
    tag: str
    is_valid: bool
    normalized_tag: str
    domain: str
    category: Optional[str] = None
    instance: Optional[str] = None
    level: int = 1
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "is_valid": self.is_valid,
            "normalized_tag": self.normalized_tag,
            "domain": self.domain,
            "category": self.category,
            "instance": self.instance,
            "level": self.level,
            "error": self.error,
        }


@dataclass
class TagIndexRecord:
    note_path: str
    raw_tags: List[str]
    normalized_tags: List[str]
    domain_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "note_path": self.note_path,
            "raw_tags": self.raw_tags,
            "normalized_tags": self.normalized_tags,
            "domain_distribution": self.domain_distribution,
        }


def lookup_domain_for_category(category: str, custom_mapping: Optional[Dict[str, str]] = None) -> str:
    """
    Look up parent domain for a given category. Defaults to 'craft' if unknown.
    """
    cat = category.strip().lower()
    mapping = custom_mapping or DEFAULT_CATEGORY_TO_DOMAIN
    return mapping.get(cat, "craft")


def validate_and_normalize_tags(
    tags: List[str], custom_mapping: Optional[Dict[str, str]] = None
) -> List[str]:
    """
    SPEC §27.4: Validate and normalize tags into strict domain/category/instance hierarchy.
    """
    normalized: List[str] = []
    for raw_tag in tags:
        clean = raw_tag.strip().lstrip("#")
        if not clean:
            continue

        parts = [p.strip().lower() for p in clean.split("/") if p.strip()]

        if not parts:
            continue

        if len(parts) == 1:
            # Bare tag: auto-resolve domain for category
            cat = parts[0]
            if cat in VALID_DOMAINS:
                # Bare domain tag
                normalized.append(f"#{cat}")
            else:
                domain = lookup_domain_for_category(cat, custom_mapping)
                normalized.append(f"#{domain}/{cat}")

        elif len(parts) == 2:
            # Check if explicit #domain/category prefix or bare domain/category
            domain_cand = parts[0]
            cat = parts[1]
            if domain_cand in VALID_DOMAINS:
                normalized.append(f"#{domain_cand}/{cat}")
            elif domain_cand in ("domain", "category", "instance"):
                # Handle #category/coding or #domain/craft
                if domain_cand == "domain" and cat in VALID_DOMAINS:
                    normalized.append(f"#{cat}")
                elif domain_cand == "category":
                    dom = lookup_domain_for_category(cat, custom_mapping)
                    normalized.append(f"#{dom}/{cat}")
                else:
                    normalized.append(f"#{domain_cand}/{cat}")
            else:
                dom = lookup_domain_for_category(domain_cand, custom_mapping)
                normalized.append(f"#{dom}/{domain_cand}/{cat}")

        else:
            # 3 or more parts: domain/category/instance
            domain_cand = parts[0]
            if domain_cand not in VALID_DOMAINS and domain_cand not in ("domain", "category", "instance"):
                dom = lookup_domain_for_category(domain_cand, custom_mapping)
                normalized.append(f"#{dom}/{'/'.join(parts)}")
            else:
                normalized.append(f"#{'/'.join(parts[:3])}")

    return normalized


class TagManager:
    """
    SPEC §27.4: 3-Level Tag Hierarchy & Semantic Indexing manager.
    """

    SWITCH_KEY = "locus.vault.tag_manager.enabled"

    def __init__(self, custom_mapping: Optional[Dict[str, str]] = None) -> None:
        self.mapping = dict(DEFAULT_CATEGORY_TO_DOMAIN)
        if custom_mapping:
            self.mapping.update(custom_mapping)
        self._note_indices: Dict[str, TagIndexRecord] = {}

    def is_tag_manager_enabled(self) -> bool:
        """Check subsystem off-switch."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def register_category_domain(self, category: str, domain: str) -> None:
        """Register category to domain mapping."""
        dom = domain.strip().lower()
        if dom in VALID_DOMAINS:
            self.mapping[category.strip().lower()] = dom

    def validate_tag(self, tag: str) -> TagValidationResult:
        """Validate single tag and determine hierarchy level."""
        clean = tag.strip().lstrip("#")
        parts = [p.strip().lower() for p in clean.split("/") if p.strip()]

        if not parts:
            return TagValidationResult(
                tag=tag,
                is_valid=False,
                normalized_tag="",
                domain="unknown",
                error="Empty tag",
            )

        norm_list = validate_and_normalize_tags([tag], self.mapping)
        norm_tag = norm_list[0] if norm_list else ""
        norm_parts = norm_tag.lstrip("#").split("/")

        lvl = len(norm_parts)
        domain = norm_parts[0] if lvl >= 1 else "unknown"
        category = norm_parts[1] if lvl >= 2 else None
        instance = norm_parts[2] if lvl >= 3 else None

        return TagValidationResult(
            tag=tag,
            is_valid=True,
            normalized_tag=norm_tag,
            domain=domain,
            category=category,
            instance=instance,
            level=min(3, lvl),
        )

    def normalize(self, tags: List[str]) -> List[str]:
        """Normalize list of tags."""
        if not self.is_tag_manager_enabled():
            return list(tags)
        return validate_and_normalize_tags(tags, self.mapping)

    def index_note(self, note_path: str, tags: List[str]) -> TagIndexRecord:
        """
        Extract, normalize, and index tags for a vault note.
        """
        normalized = self.normalize(tags)

        # Compute domain distribution
        dist: Dict[str, int] = {d: 0 for d in VALID_DOMAINS}
        for n_tag in normalized:
            clean = n_tag.lstrip("#")
            dom = clean.split("/")[0]
            if dom in dist:
                dist[dom] += 1

        rec = TagIndexRecord(
            note_path=note_path,
            raw_tags=tags,
            normalized_tags=normalized,
            domain_distribution=dist,
        )
        self._note_indices[note_path] = rec
        return rec

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""
        return {
            "indexed_notes_count": len(self._note_indices),
            "custom_mappings_count": len(self.mapping),
            "subsystem_enabled": self.is_tag_manager_enabled(),
            "valid_domains": list(VALID_DOMAINS),
        }
