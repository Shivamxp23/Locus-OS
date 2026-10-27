"""
Locus Vault package: LiveSync bridge, crawlers, and vault synchronization.
"""
from sidecar.vault.tag_manager import (
    DEFAULT_CATEGORY_TO_DOMAIN,
    VALID_DOMAINS,
    TagIndexRecord,
    TagManager,
    TagValidationResult,
    lookup_domain_for_category,
    validate_and_normalize_tags,
)

__all__ = [
    "DEFAULT_CATEGORY_TO_DOMAIN",
    "VALID_DOMAINS",
    "TagIndexRecord",
    "TagManager",
    "TagValidationResult",
    "lookup_domain_for_category",
    "validate_and_normalize_tags",
]

