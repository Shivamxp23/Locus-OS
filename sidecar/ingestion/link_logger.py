"""sidecar/ingestion/link_logger.py - Link Dump & Web Resource Logger.

Implements Spec §27.6:
- Extracts URLs from input text, strips tracking parameters (utm_*, ref, gclid).
- Derives source domains and categorizes web references.
- Formats structured Obsidian markdown resource records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from typing import List, Optional


@dataclass
class LoggedResource:
    url: str
    clean_url: str
    domain: str
    title: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    markdown_entry: str = ""


class LinkDumpLogger:
    """Extracts, cleans, and indexes web URLs into Obsidian vault format."""

    TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref"}

    URL_REGEX = re.compile(r"https?://[^\s<>\"')]+")

    def clean_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        clean_query = {k: v for k, v in query_dict.items() if k.lower() not in self.TRACKING_PARAMS}
        new_query = urlencode(clean_query, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def process_text(self, text: str, default_tag: str = "#resource") -> list[LoggedResource]:
        found_urls = self.URL_REGEX.findall(text)
        resources: list[LoggedResource] = []

        for url in set(found_urls):
            clean = self.clean_url(url)
            parsed = urlparse(clean)
            domain = parsed.netloc.lower()

            entry_md = f"- [{domain}]({clean}) {default_tag}"
            resources.append(
                LoggedResource(
                    url=url,
                    clean_url=clean,
                    domain=domain,
                    tags=[default_tag],
                    markdown_entry=entry_md,
                )
            )

        return resources
