"""Data redaction module for Locus OS sidecar."""

import re
from typing import Any, List, Tuple


class DataRedactor:
    _PATTERNS: List[Tuple[str, re.Pattern]] = [
        ("openai_key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
        ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9-]{20,}")),
        ("google_key", re.compile(r"AIza[A-Za-z0-9_-]{35}")),
        ("github_token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
        ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{36}")),
        ("slack_token", re.compile(r"xox[bpas]-[A-Za-z0-9-]+")),
        ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+")),
        ("aws_key", re.compile(r"AKIA[A-Z0-9]{16}")),
        ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}")),
        ("basic_auth", re.compile(r"Basic\s+[A-Za-z0-9+/=]{10,}")),
        ("ssh_private", re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----.*?-----END (?:RSA |EC |DSA )?PRIVATE KEY-----", re.DOTALL)),
        ("connection_string", re.compile(r"(?:postgres|mysql|mongodb|redis)://[^\s]+")),
        ("telegram_token", re.compile(r"\d{8,10}:[A-Za-z0-9_-]{35}")),
        ("generic_api_key", re.compile(r"(?i)(?:password|secret|token|apikey)\s*[=:]\s*[\"']?([^\s\"']{8,})[\"']?")),
        ("npm_token", re.compile(r"npm_[A-Za-z0-9]{36}")),
    ]

    SENSITIVE_BODY_KEYS = {"password", "secret", "token", "api_key", "access_token", "private_key"}

    def mask_token(self, token: str) -> str:
        if len(token) < 18:
            return "***REDACTED***"
        return f"{token[:6]}...{token[-4:]}"

    def redact_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        redacted = text
        for _, pattern in self._PATTERNS:
            def replacer(match: re.Match) -> str:
                if match.groups():
                    full_match = match.group(0)
                    secret = match.group(1)
                    return full_match.replace(secret, self.mask_token(secret))
                return self.mask_token(match.group(0))

            redacted = pattern.sub(replacer, redacted)
        return redacted

    def redact_structure(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: (self.mask_token(v) if isinstance(v, str) and k.lower() in self.SENSITIVE_BODY_KEYS else self.redact_structure(v))
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self.redact_structure(item) for item in obj]
        elif isinstance(obj, str):
            return self.redact_text(obj)
        else:
            return obj
