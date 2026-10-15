"""sidecar/vault/tag_manager.py - 3-Level Tag Hierarchy & Semantic Indexing.

Implements Spec §27.4:
TAG HIERARCHY STRUCTURE:
- Level 1: Domain (#domain/health, #domain/craft, #domain/leverage, #domain/expression)
- Level 2: Category (#category/exercise, #category/coding, #category/writing, etc.)
- Level 3: Instance (#instance/locus-os, #instance/deepseek, #instance/2026-08)

Provides auto-resolution of bare/unprefixed tags to domain taxonomy.
"""

from __future__ import annotations

from typing import Dict, List, Optional


DEFAULT_CATEGORY_TO_DOMAIN: dict[str, str] = {
    "exercise": "health",
    "sleep": "health",
    "nutrition": "health",
    "meditation": "health",
    "coding": "craft",
    "engineering": "craft",
    "architecture": "craft",
    "debugging": "craft",
    "finance": "leverage",
    "automation": "leverage",
    "wealth": "leverage",
    "systems": "leverage",
    "writing": "expression",
    "art": "expression",
    "music": "expression",
    "design": "expression",
}


def lookup_domain_for_category(category: str, custom_mapping: Optional[dict[str, str]] = None) -> str:
    """Resolve a category name to its parent domain."""
    mapping = custom_mapping or DEFAULT_CATEGORY_TO_DOMAIN
    cat_lower = category.lower().strip()
    return mapping.get(cat_lower, "craft")


def validate_and_normalize_tags(
    tags: list[str],
    custom_mapping: Optional[dict[str, str]] = None,
) -> list[str]:
    """Validate and normalize tags into the strict 3-level taxonomy.

    Normalization rules:
    - Removes leading '#'
    - If 1 part: resolve category -> #domain/{category}
    - If 2 parts: prepend '#' -> #{part1}/{part2}
    - If 3 parts: prepend '#' -> #{part1}/{part2}/{part3}
    - Ensures clean formatted tags without duplicates
    """
    normalized: list[str] = []
    seen: set[str] = set()

    for raw in tags:
        clean = raw.strip().lstrip("#")
        if not clean:
            continue

        parts = [p.strip().lower() for p in clean.split("/") if p.strip()]
        if not parts:
            continue

        if len(parts) == 1:
            dom = lookup_domain_for_category(parts[0], custom_mapping)
            tag_str = f"#domain/{dom}/{parts[0]}"
        elif len(parts) == 2:
            tag_str = f"#{parts[0]}/{parts[1]}"
        else:
            tag_str = f"#{'/'.join(parts[:3])}"

        if tag_str not in seen:
            seen.add(tag_str)
            normalized.append(tag_str)

    return normalized


class TagManager:
    """Manages vault tags, taxonomy validation, and semantic tag indexing."""

    def __init__(self, mapping: Optional[dict[str, str]] = None) -> None:
        self.mapping = mapping or dict(DEFAULT_CATEGORY_TO_DOMAIN)

    def normalize(self, tags: list[str]) -> list[str]:
        return validate_and_normalize_tags(tags, self.mapping)

    def register_category_domain(self, category: str, domain: str) -> None:
        self.mapping[category.lower().strip()] = domain.lower().strip()
