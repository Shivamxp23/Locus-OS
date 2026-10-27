"""
SPEC §27.6 lines 7254-7304: Link Dump & Web Resource Logger (F-0062 / US-99).
Source: Comprehensive Locus System Design.html
Logic:
    Intercepts raw URLs sent to Telegram/chat, scrapes article content,
    generates 3-bullet summaries, and archives to vault resource library:
    - title: Article Title
    - domain_category: (ai_research | systems_engineering | film_production | health_longevity)
    - key_takeaways: [3 bullet points]
    - relevance_to_goals: How this connects to active projects
    Saves notes to Obsidian /vault/03-Resources/{domain_category}/{slugify(title)}.md.
Off state:
    locus.ingestion.link_logger.enabled: when off, returns disabled status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import html
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from sidecar import config

logger = logging.getLogger("locus.ingestion.link_logger")

DOMAIN_CATEGORIES = [
    "ai_research",
    "systems_engineering",
    "film_production",
    "health_longevity",
]

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "ai_research": [
        "ai", "llm", "deepseek", "transformer", "neural", "agent", "prompt",
        "gemini", "claude", "gpt", "model", "inference", "machine learning",
    ],
    "systems_engineering": [
        "architecture", "python", "typescript", "docker", "kubernetes", "database",
        "neo4j", "fastapi", "linux", "compiler", "distributed", "engineering",
        "api", "backend", "git", "infrastructure",
    ],
    "film_production": [
        "film", "video", "cinema", "directing", "camera", "lighting", "editing",
        "screenplay", "creative", "production", "youtube", "art", "cinematography",
    ],
    "health_longevity": [
        "health", "longevity", "workout", "exercise", "sleep", "diet", "nutrition",
        "cardio", "metabolism", "fasting", "recovery", "supplement", "fitness",
    ],
}


def slugify(text: str) -> str:
    """Convert text into filesystem-safe filename slug."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[-\s]+", "-", clean).strip("-_")
    return clean[:80] or "untitled-resource"


def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def extract_readable_text(html_raw: str) -> Tuple[str, str]:
    """
    Extract article title and cleaned text from raw HTML.
    Returns (title, cleaned_text).
    """
    if not html_raw:
        return "Untitled Resource", ""

    # Title extraction
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_raw, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1).strip()) if title_match else "Untitled Resource"
    title = re.sub(r"\s+", " ", title)

    # Strip script and style blocks
    cleaned = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", html_raw, flags=re.IGNORECASE | re.DOTALL)

    # Convert block elements to newlines
    cleaned = re.sub(r"<(?:p|div|h[1-6]|li|br|tr)[^>]*>", "\n", cleaned, flags=re.IGNORECASE)

    # Strip remaining HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # Decode HTML entities
    cleaned = html.unescape(cleaned)

    # Collapse excessive whitespace
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    text = "\n".join(lines)

    return title, text


@dataclass
class LinkResourceSummary:
    """Structured summary and metadata for a processed web resource."""
    url: str
    title: str
    domain_category: str
    key_takeaways: List[str]
    relevance_to_goals: str
    user_commentary: str = ""
    excerpt: str = ""
    created_at: str = field(default_factory=now_iso)
    vault_path: Optional[str] = None

    def to_markdown(self) -> str:
        """
        Format resource note in canonical Obsidian Markdown per SPEC §27.6.
        """
        takeaways_str = "\n".join(f"- {item}" for item in self.key_takeaways) if self.key_takeaways else "- No takeaways extracted."
        user_note_str = self.user_commentary if self.user_commentary else "(none)"
        excerpt_clean = "\n> ".join(self.excerpt[:1500].splitlines()) if self.excerpt else "> (no content excerpt)"

        return (
            f"---\n"
            f"title: \"{self.title}\"\n"
            f"url: \"{self.url}\"\n"
            f"domain_category: \"{self.domain_category}\"\n"
            f"created: \"{self.created_at}\"\n"
            f"tags: [\"#resource\", \"#{self.domain_category}\"]\n"
            f"---\n\n"
            f"# {self.title}\n\n"
            f"**Source**: [{self.url}]({self.url})  \n"
            f"**Category**: `{self.domain_category}`  \n"
            f"**User Note**: {user_note_str}\n\n"
            f"## Key Takeaways\n"
            f"{takeaways_str}\n\n"
            f"## Relevance to Goals\n"
            f"{self.relevance_to_goals}\n\n"
            f"## Excerpt\n"
            f"> {excerpt_clean}\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "domain_category": self.domain_category,
            "key_takeaways": list(self.key_takeaways),
            "relevance_to_goals": self.relevance_to_goals,
            "user_commentary": self.user_commentary,
            "excerpt": self.excerpt,
            "created_at": self.created_at,
            "vault_path": self.vault_path,
        }


@dataclass
class ProcessLinkDumpResult:
    """Outcome of processing and archiving a web resource."""
    status: str
    path: Optional[str] = None
    title: Optional[str] = None
    takeaways: List[str] = field(default_factory=list)
    resource: Optional[LinkResourceSummary] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "path": self.path,
            "title": self.title,
            "takeaways": list(self.takeaways),
            "resource": self.resource.to_dict() if self.resource else None,
            "error": self.error,
        }


class LinkDumpLogger:
    """
    SPEC §27.6: Link Dump & Web Resource Logger engine.
    """

    SWITCH_KEY = "locus.ingestion.link_logger.enabled"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def is_enabled(self) -> bool:
        """Check subsystem off-switch."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def resolve_vault_path(self, custom_vault: Optional[Path] = None) -> Path:
        """Resolve base vault path."""
        if custom_vault:
            return custom_vault.resolve()
        cfg_vault = config.get("locus.vault.path")
        if cfg_vault:
            return Path(cfg_vault).resolve()
        return (config.get_locus_home() / "vault").resolve()

    def fetch_url(self, url: str) -> str:
        """
        Fetch HTML content from URL with timeout.
        """
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Locus-LinkLogger/1.0 (+http://127.0.0.1)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw_bytes = resp.read()
                return raw_bytes.decode("utf-8", errors="replace")
        except Exception as ex:
            logger.warning("Failed to fetch url %s: %s", url, ex)
            return ""

    def classify_domain(self, text: str, user_commentary: str = "") -> str:
        """
        Classify resource into one of:
        ai_research, systems_engineering, film_production, health_longevity
        """
        combined = f"{user_commentary} {text}".lower()
        scores: Dict[str, int] = {cat: 0 for cat in DOMAIN_CATEGORIES}

        for cat, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                matches = len(re.findall(r"\b" + re.escape(kw) + r"\b", combined))
                scores[cat] += matches

        best_cat = max(scores, key=lambda c: scores[c])
        if scores[best_cat] == 0:
            return "systems_engineering"
        return best_cat

    def synthesize_takeaways(self, text: str, title: str) -> List[str]:
        """
        Synthesize exactly 3 bullet takeaways from article content.
        """
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 20]

        takeaways: List[str] = []
        for s in sentences:
            if len(takeaways) >= 3:
                break
            # Avoid repeating title
            if s.lower() not in title.lower():
                takeaways.append(s)

        while len(takeaways) < 3:
            idx = len(takeaways) + 1
            takeaways.append(f"Key insight {idx} regarding {title}.")

        return takeaways[:3]

    def assess_relevance(self, domain_category: str, user_commentary: str) -> str:
        """
        Determine connection to active projects and goals.
        """
        if user_commentary.strip():
            return f"User context: {user_commentary.strip()}. Directly relates to active {domain_category.replace('_', ' ')} initiatives."

        mapping = {
            "ai_research": "Informs cognitive operating system agent reasoning and prompt engineering pipelines.",
            "systems_engineering": "Directly supports Locus sidecar architecture, data persistence, and offline infrastructure.",
            "film_production": "Applies to visual content workflows, creative direction, and narrative production.",
            "health_longevity": "Anchors personal health optimization, energy tracking, and cognitive endurance goals.",
        }
        return mapping.get(domain_category, "Relates to core architectural and cognitive goals.")

    def process_link_dump(
        self,
        url: str,
        user_commentary: str = "",
        html_content: Optional[str] = None,
        save_to_vault: bool = True,
        vault_root: Optional[Path] = None,
    ) -> ProcessLinkDumpResult:
        """
        SPEC §27.6 lines 7270-7297:
        Fetch & parse HTML, synthesize 3 takeaways, write resource note to /vault/03-Resources/.
        """
        if not self.is_enabled():
            return ProcessLinkDumpResult(
                status="DISABLED",
                error="Link logger subsystem is disabled (locus.ingestion.link_logger.enabled)",
            )

        if not url or not url.strip():
            return ProcessLinkDumpResult(
                status="ERROR",
                error="Empty URL provided",
            )

        raw_html = html_content if html_content is not None else self.fetch_url(url.strip())
        title, clean_text = extract_readable_text(raw_html)

        if not title or title == "Untitled Resource":
            # Fall back to URL domain/path slug
            path_part = url.rstrip("/").split("/")[-1]
            title = path_part.replace("-", " ").replace("_", " ").title() or "Web Resource Note"

        domain_cat = self.classify_domain(clean_text, user_commentary)
        takeaways = self.synthesize_takeaways(clean_text, title)
        relevance = self.assess_relevance(domain_cat, user_commentary)

        resource = LinkResourceSummary(
            url=url.strip(),
            title=title,
            domain_category=domain_cat,
            key_takeaways=takeaways,
            relevance_to_goals=relevance,
            user_commentary=user_commentary.strip(),
            excerpt=clean_text[:2000],
        )

        note_path_str: Optional[str] = None
        if save_to_vault:
            base_vault = self.resolve_vault_path(vault_root)
            resource_dir = base_vault / "03-Resources" / domain_cat
            resource_dir.mkdir(parents=True, exist_ok=True)

            note_slug = slugify(title)
            target_file = resource_dir / f"{note_slug}.md"
            target_file.write_text(resource.to_markdown(), encoding="utf-8")
            note_path_str = str(target_file)
            resource.vault_path = note_path_str

        return ProcessLinkDumpResult(
            status="SAVED",
            path=note_path_str,
            title=title,
            takeaways=takeaways,
            resource=resource,
        )

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""
        return {
            "subsystem_enabled": self.is_enabled(),
            "timeout_seconds": self.timeout_seconds,
            "supported_categories": list(DOMAIN_CATEGORIES),
        }
