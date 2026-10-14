"""Message sanitization module for Locus OS sidecar."""

import re
from typing import Any, Dict, List


class MessageSanitizer:
    SURROGATE_RE = re.compile(r"[\ud800-\udfff]")

    def sanitize_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        return self.SURROGATE_RE.sub("\uFFFD", text)

    def sanitize_recursive(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self.sanitize_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.sanitize_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self.sanitize_text(obj)
        else:
            return obj

    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.sanitize_recursive(msg) for msg in messages]
