"""
SPEC §27.4 lines 7152-7191: 3-Level Tag Hierarchy & Semantic Indexing Provider (F-0123 / US-97).
Modular off-switches:
- locus.3_level_tag_hierarchy_semantic_indexing.enabled (returns HTTP 503 when off)
- locus.vault.tag_manager.enabled (subsystem toggle; when off, returns unnormalized tags)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.vault.tag_manager import (
    TagIndexRecord,
    TagManager,
    TagValidationResult,
    validate_and_normalize_tags,
)

logger = logging.getLogger("locus.providers.tag_manager")


class BaseTagHierarchyProvider(ABC):
    """
    Abstract contract for 3-Level Tag Hierarchy & Semantic Indexing Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def normalize_tags(self, tags: List[str]) -> Dict[str, Any]:
        """Normalize list of tags to 3-level taxonomy."""

    @abstractmethod
    def validate_tag(self, tag: str) -> Dict[str, Any]:
        """Validate single tag and determine hierarchy level."""

    @abstractmethod
    def index_note(self, note_path: str, tags: List[str]) -> Dict[str, Any]:
        """Index note with normalized tags and domain distribution."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultTagHierarchyProvider(BaseTagHierarchyProvider):
    """
    Default provider wrapping TagManager with modular off-switch enforcement.
    """

    def __init__(self, manager: Optional[TagManager] = None) -> None:
        self.manager = manager or TagManager()

    @property
    def name(self) -> str:
        return "default_tag_hierarchy_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.3_level_tag_hierarchy_semantic_indexing.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def normalize_tags(self, tags: List[str]) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "3-Level tag hierarchy is disabled",
                "disabled": switch,
            }

        norm = self.manager.normalize(tags)
        return {
            "raw_tags": tags,
            "normalized_tags": norm,
            "count": len(norm),
        }

    def validate_tag(self, tag: str) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "3-Level tag hierarchy is disabled",
                "disabled": switch,
            }

        res: TagValidationResult = self.manager.validate_tag(tag)
        return res.to_dict()

    def index_note(self, note_path: str, tags: List[str]) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "3-Level tag hierarchy is disabled",
                "disabled": switch,
            }

        rec: TagIndexRecord = self.manager.index_note(note_path, tags)
        return rec.to_dict()

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        subsystem_enabled = self.manager.is_tag_manager_enabled()

        if not enabled:
            return {
                "status_code": 503,
                "detail": "3-Level tag hierarchy is disabled",
                "disabled": switch,
                "feature_enabled": False,
                "subsystem_enabled": subsystem_enabled,
            }

        status = self.manager.get_status()
        status["feature_enabled"] = True
        status["provider"] = self.name
        return status
