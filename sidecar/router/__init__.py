"""
SPEC §2.1-2.3: Query Router / Intent Classifier Module.
"""
from __future__ import annotations

from sidecar.router.classifier import (
    CLASSIFIER_SYSTEM_PROMPT,
    QueryRouterProvider,
    build_classifier_prompt,
    classify_query,
)

__all__ = [
    "CLASSIFIER_SYSTEM_PROMPT",
    "QueryRouterProvider",
    "build_classifier_prompt",
    "classify_query",
]
