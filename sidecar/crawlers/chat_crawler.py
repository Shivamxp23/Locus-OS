"""
SPEC §19.3 line 15 / F-0050: Multi-Platform Chat Crawler & Normalizer.
Discovers and parses external conversation dumps from ChatGPT, Claude, Cursor,
Pi, and Telegram into unified NormalizedChat structures.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.providers.chat_archiver import ChatTurn, NormalizedChat

logger = logging.getLogger("locus.crawlers.chat")

DECISION_PATTERNS = [
    re.compile(r"(?:^|\n|[.!?]\s+)\s*(?:[-*]\s*)?(?:Decided|Decision|Key Decision|We decided|Consensus):\s*([^\n]+)", re.IGNORECASE),
    re.compile(r"(?:^|\n|[.!?]\s+)\s*(?:[-*]\s*)?DECIDED:\s*([^\n]+)", re.IGNORECASE),
]


def extract_key_decisions(text: str) -> List[str]:
    """Extract bulleted key decisions from conversation text."""
    decisions: List[str] = []
    if not text:
        return decisions
    for pattern in DECISION_PATTERNS:
        for match in pattern.finditer(text):
            dec = match.group(1).strip()
            if dec and dec not in decisions:
                decisions.append(dec)
    return decisions


class ChatCrawler:
    """Discovers and parses chat dumps from various AI platforms."""

    def __init__(self, search_dirs: Optional[List[Path]] = None) -> None:
        self.search_dirs = search_dirs or []

    def get_default_crawl_dirs(self) -> List[Path]:
        """Resolve default directory locations for chat dumps."""
        locus_home = config.get_locus_home()
        configured = config.get("locus.ingestion.chat_dirs")
        dirs: List[Path] = []
        if configured and isinstance(configured, list):
            for d in configured:
                dirs.append(Path(d).resolve())
        else:
            dirs.append((locus_home / "chats").resolve())
            dirs.append((locus_home / "captures").resolve())
        return [d for d in dirs if d.exists()]

    def crawl_directory(self, directory: Path) -> List[NormalizedChat]:
        """Crawl a single directory recursively for known export file formats."""
        normalized: List[NormalizedChat] = []
        if not directory.is_dir():
            return normalized

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in (".json", ".jsonl", ".txt", ".md"):
                continue

            try:
                chats = self.parse_file(file_path)
                normalized.extend(chats)
            except Exception as ex:
                logger.debug("Skipping unparseable chat file %s: %s", file_path, ex)

        return normalized

    def parse_file(self, file_path: Path) -> List[NormalizedChat]:
        """Detect format and parse an export file."""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return []

        # Try JSON parsing first
        if file_path.suffix.lower() == ".json":
            try:
                data = json.loads(text)
                return self.parse_json_data(data, file_path)
            except json.JSONDecodeError:
                pass

        # Fallback to plain markdown transcript
        if file_path.suffix.lower() in (".md", ".txt"):
            return self.parse_markdown_transcript(text, file_path)

        return []

    def parse_json_data(self, data: Any, file_path: Path) -> List[NormalizedChat]:
        """Route parsed JSON to specific platform normalizer."""
        if isinstance(data, list):
            # ChatGPT export array or list of chats
            results: List[NormalizedChat] = []
            for item in data:
                if isinstance(item, dict) and "mapping" in item:
                    c = self._parse_chatgpt_conversation(item)
                    if c:
                        results.append(c)
                elif isinstance(item, dict) and "chat_messages" in item:
                    c = self._parse_claude_conversation(item)
                    if c:
                        results.append(c)
            if results:
                return results

        elif isinstance(data, dict):
            # ChatGPT single conversation
            if "mapping" in data:
                c = self._parse_chatgpt_conversation(data)
                return [c] if c else []

            # Claude Web / Desktop export
            if "chat_messages" in data:
                c = self._parse_claude_conversation(data)
                return [c] if c else []

            # Cursor IDE conversation log
            if "conversation" in data or "cursor_version" in data:
                c = self._parse_cursor_conversation(data, file_path)
                return [c] if c else []

            # Pi native session dump
            if "session_id" in data and ("turns" in data or "messages" in data):
                c = self._parse_pi_conversation(data, file_path)
                return [c] if c else []

            # Telegram exported chat log
            if "messages" in data and ("type" in data or "name" in data):
                c = self._parse_telegram_conversation(data, file_path)
                return [c] if c else []

        return []

    def _parse_chatgpt_conversation(self, data: Dict[str, Any]) -> Optional[NormalizedChat]:
        """Normalize ChatGPT export object."""
        title = data.get("title") or "ChatGPT Conversation"
        create_time = data.get("create_time")
        date_str = (
            datetime.fromtimestamp(create_time, timezone.utc).strftime("%Y-%m-%d")
            if create_time
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        turns: List[ChatTurn] = []
        all_text = ""
        mapping = data.get("mapping", {})

        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue
            author = msg.get("author", {})
            role = author.get("role", "unknown")
            if role in ("system",):
                continue

            content_obj = msg.get("content", {})
            parts = content_obj.get("parts", [])
            text_parts = [str(p) for p in parts if isinstance(p, str)]
            body = "\n".join(text_parts).strip()
            if not body:
                continue

            all_text += "\n" + body
            turns.append(ChatTurn(role="user" if role == "user" else "assistant", content=body))

        if not turns:
            return None

        model = data.get("model", "gpt-4")
        return NormalizedChat(
            title=title,
            platform="chatgpt",
            model=model,
            date=date_str,
            turns=turns,
            key_decisions=extract_key_decisions(all_text),
            tags=["chatgpt", "ai-chat"],
        )

    def _parse_claude_conversation(self, data: Dict[str, Any]) -> Optional[NormalizedChat]:
        """Normalize Claude export object."""
        title = data.get("name") or data.get("title") or "Claude Conversation"
        created_at = data.get("created_at") or data.get("date")
        date_str = created_at[:10] if created_at and len(created_at) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")

        turns: List[ChatTurn] = []
        all_text = ""
        raw_msgs = data.get("chat_messages", [])

        for msg in raw_msgs:
            sender = msg.get("sender", "human")
            role = "user" if sender in ("human", "user") else "assistant"
            text = msg.get("text") or msg.get("content", "")
            if not text.strip():
                continue
            all_text += "\n" + text
            turns.append(ChatTurn(role=role, content=text.strip(), timestamp=msg.get("created_at")))

        if not turns:
            return None

        model = data.get("model", "claude-3-5-sonnet")
        return NormalizedChat(
            title=title,
            platform="claude",
            model=model,
            date=date_str,
            turns=turns,
            key_decisions=extract_key_decisions(all_text),
            tags=["claude", "ai-chat"],
        )

    def _parse_cursor_conversation(self, data: Dict[str, Any], file_path: Path) -> Optional[NormalizedChat]:
        """Normalize Cursor IDE conversation export."""
        title = data.get("title") or file_path.stem.replace("_", " ").title()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        msgs = data.get("conversation") or data.get("messages", [])

        turns: List[ChatTurn] = []
        all_text = ""
        for m in msgs:
            role = m.get("role", "user")
            content = m.get("text") or m.get("content", "")
            if not content.strip():
                continue
            all_text += "\n" + content
            turns.append(ChatTurn(role=role, content=content.strip()))

        if not turns:
            return None

        return NormalizedChat(
            title=title,
            platform="cursor",
            model=data.get("model", "cursor-fast"),
            date=date_str,
            turns=turns,
            key_decisions=extract_key_decisions(all_text),
            tags=["cursor", "ide-chat"],
        )

    def _parse_pi_conversation(self, data: Dict[str, Any], file_path: Path) -> Optional[NormalizedChat]:
        """Normalize native Pi agent conversation."""
        title = data.get("title") or file_path.stem.replace("_", " ").title()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        turns_data = data.get("turns") or data.get("messages", [])

        turns: List[ChatTurn] = []
        all_text = ""
        for t in turns_data:
            role = t.get("role", "user")
            content = t.get("content", "")
            all_text += "\n" + content
            turns.append(ChatTurn(role=role, content=content.strip(), timestamp=t.get("timestamp")))

        if not turns:
            return None

        return NormalizedChat(
            title=title,
            platform="pi",
            model=data.get("model", "pi-native"),
            date=date_str,
            turns=turns,
            key_decisions=extract_key_decisions(all_text),
            tags=["pi", "agent-chat"],
        )

    def _parse_telegram_conversation(self, data: Dict[str, Any], file_path: Path) -> Optional[NormalizedChat]:
        """Normalize Telegram exported chat history."""
        title = data.get("name") or "Telegram Chat"
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        messages = data.get("messages", [])

        turns: List[ChatTurn] = []
        all_text = ""
        for m in messages:
            if m.get("type") != "message":
                continue
            sender = m.get("from", "User")
            text = m.get("text")
            if isinstance(text, list):
                # Telegram rich text blocks
                text = "".join(p if isinstance(p, str) else p.get("text", "") for p in text)
            if not text or not str(text).strip():
                continue
            body = str(text).strip()
            all_text += "\n" + body
            role = "assistant" if "bot" in sender.lower() or "locus" in sender.lower() else "user"
            turns.append(ChatTurn(role=role, content=body, timestamp=m.get("date")))

        if not turns:
            return None

        return NormalizedChat(
            title=title,
            platform="telegram",
            model="telegram-bot",
            date=date_str,
            turns=turns,
            key_decisions=extract_key_decisions(all_text),
            tags=["telegram", "gateway-chat"],
        )

    def parse_markdown_transcript(self, text: str, file_path: Path) -> List[NormalizedChat]:
        """Parse raw transcript markdown file into normalized turns."""
        title = file_path.stem.replace("_", " ").title()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Split turns by markdown headings like ### User / ### Assistant
        blocks = re.split(r"(?:^|\n)###?\s*(User|Human|Assistant|AI|Claude|ChatGPT):?", text, flags=re.IGNORECASE)
        turns: List[ChatTurn] = []

        if len(blocks) > 1:
            for i in range(1, len(blocks), 2):
                role_label = blocks[i].lower()
                content = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
                role = "assistant" if role_label in ("assistant", "ai", "claude", "chatgpt") else "user"
                if content:
                    turns.append(ChatTurn(role=role, content=content))
        else:
            turns.append(ChatTurn(role="user", content=text.strip()))

        return [
            NormalizedChat(
                title=title,
                platform="transcript",
                model="unknown",
                date=date_str,
                turns=turns,
                key_decisions=extract_key_decisions(text),
                tags=["transcript"],
            )
        ]
