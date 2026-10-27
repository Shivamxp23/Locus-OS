"""
SPEC §27.5 lines 7192-7251: Rough Note Parser & Idea Tracker (F-0061 / US-98).
Source: Comprehensive Locus System Design.html + locus_microsystems.html
Logic:
    Converts raw unstructured brain dumps from Telegram, voice_stt, or quick_note
    into structured Obsidian atomic notes with frontmatter, tasks, and entity links:
    1. Canonical Title (3-6 words)
    2. Primary Faction Tag (#domain/craft, #domain/health, etc.)
    3. Core Proposition (1-2 sentences)
    4. Extracted Action Items (with checkboxes)
    5. Named Entities (people, tools, concepts)
    Saves notes to Obsidian /vault/04-Captures/Inbox/{slugify(title)}.md.
Off state:
    locus.ingestion.rough_note_parser.enabled: when off, parsing returns unparsed or disabled status.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar import config

logger = logging.getLogger("locus.ingestion.rough_note_parser")

FACTION_KEYWORDS: Dict[str, Set[str]] = {
    "health": {
        "exercise", "workout", "gym", "sleep", "diet", "recovery", "health",
        "nutrition", "cardio", "doctor", "run", "running", "steps", "supplements",
        "meditation", "water", "meal", "food", "training",
    },
    "craft": {
        "code", "coding", "locus", "python", "typescript", "build", "architecture",
        "design", "feature", "repo", "software", "git", "api", "backend",
        "frontend", "debug", "refactor", "database", "neo4j", "test", "tests",
    },
    "leverage": {
        "business", "money", "client", "revenue", "finance", "invest", "investing",
        "sales", "career", "contract", "market", "pricing", "invoice", "capital",
        "equity", "profit", "deal", "growth",
    },
    "expression": {
        "write", "writing", "article", "video", "youtube", "content", "post",
        "creative", "art", "podcast", "tweet", "essay", "blog", "draw", "music",
        "publish", "camera", "film",
    },
}

KNOWN_ENTITIES: Set[str] = {
    "Obsidian", "Telegram", "Neo4j", "Python", "TypeScript", "FastAPI",
    "Docker", "Git", "GitHub", "LiveSync", "Syncthing", "Locus", "Pi",
    "Claude", "Gemini", "DeepSeek", "Android", "Linux", "Windows",
}


def slugify(text: str) -> str:
    """Convert text into filesystem-safe filename slug."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[-\s]+", "-", clean).strip("-_")
    return clean[:80] or "untitled-note"


def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoughNote:
    """Structured representation of an extracted rough note."""
    title: str
    primary_tag: str
    core_proposition: str
    action_items: List[str]
    entities: List[str]
    raw_text: str
    source: str = "telegram"
    created_at: str = field(default_factory=now_iso)
    vault_path: Optional[str] = None

    def to_markdown(self) -> str:
        """
        Render note into canonical Obsidian Markdown format per SPEC §27.5.
        """
        entities_str = ", ".join(f'"{e}"' for e in self.entities) if self.entities else ""
        actions_str = "\n".join(f"- [ ] {item}" for item in self.action_items) if self.action_items else "- [ ] None identified"
        
        raw_quoted = "\n> ".join(self.raw_text.splitlines()) if self.raw_text else "> (empty capture)"

        return (
            f"---\n"
            f"title: \"{self.title}\"\n"
            f"created: \"{self.created_at}\"\n"
            f"source: \"{self.source}\"\n"
            f"tags: [\"{self.primary_tag}\"]\n"
            f"entities: [{entities_str}]\n"
            f"---\n\n"
            f"# {self.title}\n\n"
            f"## Summary\n"
            f"{self.core_proposition}\n\n"
            f"## Action Items\n"
            f"{actions_str}\n\n"
            f"## Raw Capture\n"
            f"> {raw_quoted}\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "primary_tag": self.primary_tag,
            "core_proposition": self.core_proposition,
            "action_items": list(self.action_items),
            "entities": list(self.entities),
            "raw_text": self.raw_text,
            "source": self.source,
            "created_at": self.created_at,
            "vault_path": self.vault_path,
        }


@dataclass
class ParseRoughNoteResult:
    """Outcome of parsing and ingesting a rough note."""
    success: bool
    path: Optional[str] = None
    tasks_created: int = 0
    note: Optional[RoughNote] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path": self.path,
            "tasks_created": self.tasks_created,
            "note": self.note.to_dict() if self.note else None,
            "error": self.error,
        }


class RoughNoteParser:
    """
    SPEC §27.5: Rough Note Parser & Idea Tracker engine.
    """

    SWITCH_KEY = "locus.ingestion.rough_note_parser.enabled"

    def __init__(self, default_source: str = "telegram") -> None:
        self.default_source = default_source

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

    def extract_title(self, raw_text: str) -> str:
        """
        Extract canonical title (3-6 words).
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return "Rough Note Capture"

        first_line = lines[0].lstrip("#-*> ").strip()
        words = first_line.split()

        if 3 <= len(words) <= 6:
            return " ".join(words).title()
        elif len(words) > 6:
            # First 5 words
            return " ".join(words[:5]).title()
        elif len(words) >= 1:
            # Pad with subsequent line words if available
            cand = list(words)
            if len(lines) > 1:
                cand.extend(lines[1].lstrip("#-*> ").strip().split())
            cand = cand[:5]
            if len(cand) < 3:
                cand.append("Note")
            return " ".join(cand).title()

        return "Rough Note Capture"

    def extract_faction_tag(self, raw_text: str) -> str:
        """
        Determine primary faction tag: #domain/craft, #domain/health, etc.
        """
        lower = raw_text.lower()
        counts: Dict[str, int] = {k: 0 for k in FACTION_KEYWORDS}

        for faction, kw_set in FACTION_KEYWORDS.items():
            for kw in kw_set:
                matches = len(re.findall(r"\b" + re.escape(kw) + r"\b", lower))
                counts[faction] += matches

        best_faction = max(counts, key=lambda f: counts[f])
        if counts[best_faction] == 0:
            return "#domain/craft"
        return f"#domain/{best_faction}"

    def extract_core_proposition(self, raw_text: str) -> str:
        """
        Extract core proposition (1-2 sentences).
        """
        cleaned = re.sub(r"^[#-*>]\s*", "", raw_text, flags=re.MULTILINE).strip()
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

        if not valid_sentences:
            return raw_text.strip() or "Raw capture entry."

        if len(valid_sentences) == 1:
            return valid_sentences[0]
        return f"{valid_sentences[0]} {valid_sentences[1]}"

    def extract_action_items(self, raw_text: str) -> List[str]:
        """
        Extract action items from checkbox lines, TODO markers, or imperatives.
        """
        actions: List[str] = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            # Checkbox matches: - [ ] Task, * [ ] Task, [ ] Task
            cb_match = re.match(r"^[-*]?\s*\[\s*\]\s*(.*)$", stripped)
            if cb_match:
                item = cb_match.group(1).strip()
                if item:
                    actions.append(item)
                continue

            # Marker matches: TODO: task, Task: task, Need to task
            marker_match = re.match(r"^(?:TODO|TASK|Action|Next|Remember)\s*:\s*(.*)$", stripped, re.IGNORECASE)
            if marker_match:
                item = marker_match.group(1).strip()
                if item:
                    actions.append(item)
                continue

            # Bullet points indicating actionable verbs
            bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
            if bullet_match:
                content = bullet_match.group(1).strip()
                lower_content = content.lower()
                if any(lower_content.startswith(verb) for verb in ("need to", "must", "buy", "fix", "call", "send", "write", "finish", "implement", "deploy", "review", "schedule")):
                    actions.append(content)

        return actions

    def extract_entities(self, raw_text: str) -> List[str]:
        """
        Extract named entities (tools, @mentions, CamelCase words).
        """
        entities: Set[str] = set()

        # Check known entity dictionary
        for ent in KNOWN_ENTITIES:
            if re.search(r"\b" + re.escape(ent) + r"\b", raw_text, re.IGNORECASE):
                entities.add(ent)

        # Mentions like @username
        mentions = re.findall(r"@([A-Za-z0-9_]+)", raw_text)
        for m in mentions:
            entities.add(f"@{m}")

        # CamelCase terms (e.g. RoughNoteParser, LiveSync)
        camel_cases = re.findall(r"\b([A-Z][a-z]+[A-Z][A-Za-z0-9]*)\b", raw_text)
        for c in camel_cases:
            entities.add(c)

        return sorted(entities)

    def parse_rough_note_stream(
        self,
        raw_text: str,
        source: Optional[str] = None,
        save_to_vault: bool = True,
        vault_root: Optional[Path] = None,
    ) -> ParseRoughNoteResult:
        """
        SPEC §27.5 lines 7208-7246:
        Parse raw thought stream, generate Obsidian note, save to 04-Captures/Inbox,
        and return outcome.
        """
        if not self.is_enabled():
            return ParseRoughNoteResult(
                success=False,
                error="Rough note parser subsystem is disabled (locus.ingestion.rough_note_parser.enabled)",
            )

        if not raw_text or not raw_text.strip():
            return ParseRoughNoteResult(
                success=False,
                error="Empty raw text stream provided",
            )

        src = source or self.default_source
        title = self.extract_title(raw_text)
        primary_tag = self.extract_faction_tag(raw_text)
        core_prop = self.extract_core_proposition(raw_text)
        action_items = self.extract_action_items(raw_text)
        entities = self.extract_entities(raw_text)

        note = RoughNote(
            title=title,
            primary_tag=primary_tag,
            core_proposition=core_prop,
            action_items=action_items,
            entities=entities,
            raw_text=raw_text.strip(),
            source=src,
        )

        vault_path_str: Optional[str] = None
        if save_to_vault:
            base_vault = self.resolve_vault_path(vault_root)
            inbox_dir = base_vault / "04-Captures" / "Inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)

            note_slug = slugify(title)
            target_file = inbox_dir / f"{note_slug}.md"
            target_file.write_text(note.to_markdown(), encoding="utf-8")
            vault_path_str = str(target_file)
            note.vault_path = vault_path_str

        return ParseRoughNoteResult(
            success=True,
            path=vault_path_str,
            tasks_created=len(action_items),
            note=note,
        )

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic status for rough note parser."""
        return {
            "subsystem_enabled": self.is_enabled(),
            "default_source": self.default_source,
            "known_entities_count": len(KNOWN_ENTITIES),
            "faction_categories": list(FACTION_KEYWORDS.keys()),
        }
