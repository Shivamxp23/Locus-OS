"""
SPEC §13.8 lines 3438-3512:
Data Redaction and Credential Scrubbing (F-0041 / US-73).

Implements:
1. Vendor-specific API key patterns (OpenAI, Anthropic, Google, GitHub, Slack, AWS, Stripe, HuggingFace, JWT, private keys).
2. SENSITIVE_QUERY_PARAMS and SENSITIVE_BODY_KEYS scrubbing.
3. mask_token(token):
   Short tokens (<18 chars) fully masked (***REDACTED***);
   Longer tokens preserve first 6 + last 4 chars for debuggability (token[:6] + "..." + token[-4:]).
4. redact_sensitive_text and redact_structure.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

# Sensitive URL query parameters
SENSITIVE_QUERY_PARAMS: Set[str] = {
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "api_key",
    "apikey",
    "client_secret",
    "password",
    "auth",
    "jwt",
    "session",
    "secret",
    "key",
    "code",
    "signature",
    "x-amz-signature",
}

# Sensitive dictionary/JSON body keys
SENSITIVE_BODY_KEYS: Set[str] = {
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "api_key",
    "apikey",
    "client_secret",
    "password",
    "auth",
    "jwt",
    "session",
    "secret",
    "private_key",
    "authorization",
    "key",
}

# Vendor-specific API key patterns
KEY_PATTERNS: List[Dict[str, Union[str, re.Pattern]]] = [
    {
        "vendor": "OpenAI",
        "pattern": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    },
    {
        "vendor": "Anthropic",
        "pattern": re.compile(r"\bsk-ant-[a-zA-Z0-9\-_]{20,}\b"),
    },
    {
        "vendor": "Google",
        "pattern": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    },
    {
        "vendor": "GitHub Classic PAT",
        "pattern": re.compile(r"\bghp_[a-zA-Z0-9]{30,}\b"),
    },
    {
        "vendor": "GitHub Fine-Grained PAT",
        "pattern": re.compile(r"\bgithub_pat_[a-zA-Z0-9_]{82}\b"),
    },
    {
        "vendor": "GitHub OAuth",
        "pattern": re.compile(r"\bgho_[a-zA-Z0-9]{36}\b"),
    },
    {
        "vendor": "Slack Token",
        "pattern": re.compile(r"\bxox[baprs]-[0-9a-zA-Z\-]{10,}\b"),
    },
    {
        "vendor": "AWS Access Key",
        "pattern": re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
    },
    {
        "vendor": "Stripe Key",
        "pattern": re.compile(r"\bsk_(live|test)_[0-9a-zA-Z]{24,}\b"),
    },
    {
        "vendor": "HuggingFace Token",
        "pattern": re.compile(r"\bhf_[a-zA-Z0-9]{34,}\b"),
    },
    {
        "vendor": "Bearer Authorization",
        "pattern": re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
    },
    {
        "vendor": "JWT Token",
        "pattern": re.compile(r"\beyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b"),
    },
    {
        "vendor": "Private Key",
        "pattern": re.compile(
            r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[^-]+-----END (?:[A-Z]+ )?PRIVATE KEY-----",
            re.DOTALL,
        ),
    },
]


def mask_token(token: str) -> str:
    """
    SPEC §13.8:
    FUNCTION mask_token(token):
        IF len(token) < 18:
            RETURN "***REDACTED***"                    // fully masked (too short to safely preview)
        ELSE:
            RETURN token[:6] + "..." + token[-4:]      // preserve first 6 + last 4 for debugging
    """
    if not token:
        return "***REDACTED***"
    s = str(token).strip()
    if len(s) < 18:
        return "***REDACTED***"
    return f"{s[:6]}...{s[-4:]}"


class DataRedactor:
    """
    SPEC §13.8: Core Data Redactor engine.
    Scrubs API keys, secrets, tokens, query params, and JSON structures.
    """

    def __init__(self, custom_patterns: Optional[List[str]] = None):
        self.custom_patterns = custom_patterns or []
        self._compiled_custom: List[re.Pattern] = []
        for pat in self.custom_patterns:
            try:
                self._compiled_custom.append(re.compile(pat))
            except Exception as e:
                logger.warning(f"Failed to compile custom redaction pattern {pat}: {e}")

    def redact_sensitive_text(self, text: str) -> str:
        """
        SPEC §13.8: FUNCTION redact_sensitive_text(text)
        """
        if not text:
            return text

        result = str(text)

        # 1. Vendor API key pattern replacement
        for rule in KEY_PATTERNS:
            pat = rule["pattern"]
            assert isinstance(pat, re.Pattern)

            def _repl(match: re.Match) -> str:
                # Handle group replacement for Bearer tokens
                if match.re.pattern.startswith("(Bearer"):
                    prefix = match.group(1)
                    token = match.group(2)
                    return f"{prefix}{mask_token(token)}"
                raw = match.group(0)
                return mask_token(raw)

            result = pat.sub(_repl, result)

        # 2. Custom patterns
        for pat in self._compiled_custom:
            def _custom_repl(match: re.Match) -> str:
                raw = match.group(0)
                return mask_token(raw)

            result = pat.sub(_custom_repl, result)

        # 3. Query string redaction in URLs
        result = self._redact_url_query_params(result)

        return result

    def _redact_url_query_params(self, text: str) -> str:
        """Redact sensitive query parameters in embedded URLs."""
        # Regex finding query params: (?<=[\?&])(key)=([^&\s]+)
        def _param_repl(match: re.Match) -> str:
            prefix = match.group(1)
            key = match.group(2)
            val = match.group(3)
            if key.lower() in SENSITIVE_QUERY_PARAMS:
                return f"{prefix}{key}={mask_token(val)}"
            return match.group(0)

        # Match (delimiter)(key)=(val)
        pattern = re.compile(r"([?&])([a-zA-Z0-9_\-]+)=([^&\s\"'<>]+)")
        return pattern.sub(_param_repl, text)

    def redact_structure(self, payload: Any) -> Any:
        """
        SPEC §13.8: FUNCTION redact_structure(payload)
        Walks nested dicts and lists recursively and redacts sensitive keys and values.
        """
        if isinstance(payload, dict):
            redacted_dict: Dict[str, Any] = {}
            for k, v in payload.items():
                k_str = str(k)
                if k_str.lower() in SENSITIVE_BODY_KEYS:
                    if isinstance(v, str):
                        redacted_dict[k_str] = mask_token(v)
                    elif v is None:
                        redacted_dict[k_str] = None
                    else:
                        redacted_dict[k_str] = "***REDACTED***"
                else:
                    redacted_dict[k_str] = self.redact_structure(v)
            return redacted_dict

        if isinstance(payload, list):
            return [self.redact_structure(item) for item in payload]

        if isinstance(payload, str):
            return self.redact_sensitive_text(payload)

        return payload
