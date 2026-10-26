"""
SPEC §13.10 lines 3599-3668:
Message Sanitization (F-0043 / US-75).

Stateless sanitization helpers:
- Fixes lone surrogate code points (U+D800-U+DFFF) that crash json.dumps() and UTF-8 encoding in OpenAI SDK.
- Walks nested dict/list payloads for deep sanitization (e.g. reasoning_details, tool_calls).
- Replaces invalid surrogates with U+FFFD Unicode replacement character.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)

# Lone surrogates regex: U+D800 to U+DFFF
SURROGATE_RE: re.Pattern = re.compile(r"[\ud800-\udfff]")


def sanitize_surrogates(text: str) -> str:
    """
    SPEC §13.10 line 3614:
    FUNCTION sanitize_surrogates(text):
        IF SURROGATE_RE.search(text):
            RETURN SURROGATE_RE.replace_all(text, "\uFFFD")  // U+FFFD replacement character
        RETURN text  // fast no-op when clean
    """
    if not isinstance(text, str):
        return text
    if SURROGATE_RE.search(text):
        return SURROGATE_RE.sub("\ufffd", text)
    return text


def sanitize_structure_surrogates(payload: Any) -> Tuple[Any, bool]:
    """
    SPEC §13.10 line 3620:
    FUNCTION sanitize_structure_surrogates(payload):
        Walks nested dict/list payloads recursively.
        Returns (sanitized_payload, found_surrogates).
    """
    found = False

    def _walk(node: Any) -> Any:
        nonlocal found
        if isinstance(node, dict):
            out_dict: Dict[str, Any] = {}
            for k, v in node.items():
                k_clean = sanitize_surrogates(str(k)) if isinstance(k, str) else k
                if isinstance(v, str):
                    if SURROGATE_RE.search(v):
                        found = True
                        out_dict[k_clean] = sanitize_surrogates(v)
                    else:
                        out_dict[k_clean] = v
                elif isinstance(v, (dict, list)):
                    out_dict[k_clean] = _walk(v)
                else:
                    out_dict[k_clean] = v
            return out_dict

        if isinstance(node, list):
            out_list: List[Any] = []
            for item in node:
                if isinstance(item, str):
                    if SURROGATE_RE.search(item):
                        found = True
                        out_list.append(sanitize_surrogates(item))
                    else:
                        out_list.append(item)
                elif isinstance(item, (dict, list)):
                    out_list.append(_walk(item))
                else:
                    out_list.append(item)
            return out_list

        if isinstance(node, str):
            if SURROGATE_RE.search(node):
                found = True
                return sanitize_surrogates(node)
            return node

        return node

    sanitized = _walk(payload)
    return sanitized, found


def sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    SPEC §13.10 line 3644:
    FUNCTION sanitize_messages(messages):
        Apply to entire message list before sending to LLM API.
    """
    if not isinstance(messages, list):
        return messages

    cleaned_messages: List[Dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            cleaned_messages.append(msg)
            continue

        c = copy.deepcopy(msg)

        # 1. Message content string
        if "content" in c and isinstance(c["content"], str):
            c["content"] = sanitize_surrogates(c["content"])
        elif "content" in c and isinstance(c["content"], (list, dict)):
            c["content"], _ = sanitize_structure_surrogates(c["content"])

        # 2. Tool calls
        if "tool_calls" in c and c["tool_calls"]:
            c["tool_calls"], _ = sanitize_structure_surrogates(c["tool_calls"])

        # 3. Structured / metadata fields
        for field in ("reasoning_details", "metadata", "extra"):
            if field in c and c[field]:
                c[field], _ = sanitize_structure_surrogates(c[field])

        cleaned_messages.append(c)

    return cleaned_messages


class MessageSanitizer:
    """
    SPEC §13.10: Stateless pure helper class for message and structure sanitization.
    """

    @staticmethod
    def sanitize_text(text: str) -> str:
        return sanitize_surrogates(text)

    @staticmethod
    def sanitize_structure(payload: Any) -> Tuple[Any, bool]:
        return sanitize_structure_surrogates(payload)

    @staticmethod
    def sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sanitize_messages(messages)
