"""
Memory Provider Interface & Stackable Memory Manager (SPEC §4.18: Memory Provider Interface).
Adapted from Hermes agent/memory_provider.py + agent/memory_manager.py for Locus OS.
Provides:
  - MemoryProvider ABC with full lifecycle, prefetch, sync_turn, tool schemas, and hook contracts.
  - Stackable MemoryManager allowing multi-provider memory layers (primary + secondary providers).
"""
from __future__ import annotations

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import sidecar.config as config

logger = logging.getLogger(__name__)


class MemoryProvider(ABC):
    """
    SPEC §4.18 lines 5248-5281:
    Abstract base class for all memory providers.
    """

    def __init__(self, name: str = "default_memory") -> None:
        self.name: str = name
        self.is_initialized: bool = False
        self.active_session_id: Optional[str] = None
        self.runtime_kwargs: Dict[str, Any] = {}

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check configuration and local dependencies.
        Must NOT perform network calls or blocking operations.
        """
        raise NotImplementedError

    @abstractmethod
    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """
        Initialize provider for session, connecting resources and setting runtime context.
        Kwargs may include: hermes_home, platform, agent_context, agent_identity, parent_session_id, user_id.
        """
        raise NotImplementedError

    @abstractmethod
    def system_prompt_block(self) -> str:
        """Static text or guidance to inject into the system prompt."""
        raise NotImplementedError

    @abstractmethod
    def prefetch(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Recall context BEFORE each LLM call.
        Must be fast — return cached or quick-lookup results.
        """
        raise NotImplementedError

    @abstractmethod
    def queue_prefetch(self, query: str, session_id: Optional[str] = None) -> None:
        """Queue background recall for the NEXT turn."""
        raise NotImplementedError

    @abstractmethod
    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        session_id: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Persist completed turn.
        Must be non-blocking (e.g. queue for background worker or fast local append).
        """
        raise NotImplementedError

    @abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return tool definitions to expose to the model."""
        raise NotImplementedError

    @abstractmethod
    def handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool call and return JSON-formatted result string."""
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully close connections and flush pending background work."""
        raise NotImplementedError

    # ---------------- Optional lifecycle hooks ---------------- #

    def on_turn_start(self, turn_number: int, message: Dict[str, Any], **kwargs: Any) -> None:
        """Invoked when an agent turn begins."""
        pass

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Invoked when an agent session concludes."""
        pass

    def on_session_switch(
        self,
        new_session_id: str,
        parent_session_id: Optional[str] = None,
        reset: bool = False,
        rewound: bool = False,
    ) -> None:
        """Invoked when a session splits, resets, or rotates."""
        self.active_session_id = new_session_id

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract insights from messages about to be compacted or compressed."""
        return None

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mirror external or built-in memory write operations."""
        pass

    def on_delegation(self, task: str, result: Any, child_session_id: str) -> None:
        """Observe subagent delegation outcomes."""
        pass


class DefaultMemoryProvider(MemoryProvider):
    """
    Concrete default reference memory provider for local sessions.
    Stores episodic turns in memory and provides keyword-based recall.
    """

    def __init__(self, name: str = "default_memory") -> None:
        super().__init__(name=name)
        self._turns: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._prefetched_cache: Dict[str, str] = {}

    def is_available(self) -> bool:
        val = config.get("locus.memory.enabled")
        if val is not None and not config.is_enabled("locus.memory.enabled"):
            return False
        return True

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self.active_session_id = session_id
        self.runtime_kwargs = dict(kwargs)
        self.is_initialized = True

    def system_prompt_block(self) -> str:
        return f"[MemoryProvider: {self.name} active. Retains session dialog and recall context.]"

    def prefetch(self, query: str, session_id: Optional[str] = None) -> str:
        sid = session_id or self.active_session_id or ""
        cache_key = f"{sid}:{query}"
        with self._lock:
            if cache_key in self._prefetched_cache:
                return self._prefetched_cache[cache_key]

        # Fast local search across stored turns
        q_lower = query.lower()
        matched: List[str] = []
        with self._lock:
            for turn in reversed(self._turns):
                if q_lower in turn.get("user", "").lower() or q_lower in turn.get("assistant", "").lower():
                    matched.append(f"Turn: User asked '{turn.get('user')[:80]}', Assistant answered '{turn.get('assistant')[:80]}'")
                    if len(matched) >= 3:
                        break

        summary = "\n".join(matched) if matched else "No previous turn matches."
        with self._lock:
            self._prefetched_cache[cache_key] = summary
        return summary

    def queue_prefetch(self, query: str, session_id: Optional[str] = None) -> None:
        # Pre-warm cache synchronously for default provider
        self.prefetch(query, session_id=session_id)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        session_id: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        with self._lock:
            self._turns.append({
                "session_id": session_id or self.active_session_id,
                "user": user_content,
                "assistant": assistant_content,
                "messages_count": len(messages) if messages else 0,
            })

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"{self.name}_search",
                    "description": "Search local memory turns for past decisions and facts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search terms to match in past turns"}
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name == f"{self.name}_search":
            query = str(args.get("query", ""))
            return json.dumps({"status": "ok", "result": self.prefetch(query)})
        return json.dumps({"error": f"Unknown tool {tool_name}"})

    def shutdown(self) -> None:
        with self._lock:
            self._prefetched_cache.clear()
            self._turns.clear()
            self.is_initialized = False


class MemoryManager:
    """
    SPEC §4.18 lines 5282-5309:
    Stackable Memory Manager: manages primary and secondary memory providers,
    aggregating prefetch context and dispatching turn updates.
    """

    def __init__(self) -> None:
        self.primary_provider: Optional[MemoryProvider] = None
        self.active_providers: List[MemoryProvider] = []
        self._lock = threading.Lock()

    def register_provider(
        self,
        provider: MemoryProvider,
        session_id: str = "default_session",
        is_primary: bool = False,
        **runtime_kwargs: Any,
    ) -> bool:
        """
        SPEC §4.18 line 5287-5290:
        register_provider(provider):
            IF provider.is_available():
                provider.initialize(session_id, **runtime_kwargs)
                active_providers.append(provider)
        """
        if not provider.is_available():
            logger.info(f"Memory provider {provider.name} is not available, skipping.")
            return False

        provider.initialize(session_id=session_id, **runtime_kwargs)
        with self._lock:
            if provider not in self.active_providers:
                if is_primary or self.primary_provider is None:
                    self.primary_provider = provider
                    self.active_providers.insert(0, provider)
                else:
                    self.active_providers.append(provider)
        return True

    def get_primary_provider(self) -> Optional[MemoryProvider]:
        with self._lock:
            return self.primary_provider

    def get_active_providers(self) -> List[MemoryProvider]:
        with self._lock:
            return list(self.active_providers)

    def prefetch_all(self, query: str, session_id: Optional[str] = None) -> str:
        """
        SPEC §4.18 line 5292-5296:
        prefetch_all(query):
            results = []
            FOR EACH provider IN active_providers:
                results.append(provider.prefetch(query))
            RETURN merge_results(results)
        """
        with self._lock:
            providers = list(self.active_providers)

        blocks: List[str] = []
        for prov in providers:
            try:
                res = prov.prefetch(query, session_id=session_id)
                if res and res.strip():
                    blocks.append(f"[{prov.name}]:\n{res.strip()}")
            except Exception as exc:
                logger.warning(f"Error during prefetch in {prov.name}: {exc}")

        return "\n\n".join(blocks) if blocks else ""

    def queue_prefetch_all(self, query: str, session_id: Optional[str] = None) -> None:
        with self._lock:
            providers = list(self.active_providers)

        for prov in providers:
            try:
                prov.queue_prefetch(query, session_id=session_id)
            except Exception as exc:
                logger.warning(f"Error queuing prefetch in {prov.name}: {exc}")

    def sync_turn_all(
        self,
        user_content: str,
        assistant_content: str,
        session_id: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        SPEC §4.18 line 5298-5301:
        sync_turn_all(user, assistant):
            FOR EACH provider IN active_providers:
                provider.sync_turn(user, assistant)  // non-blocking
        """
        with self._lock:
            providers = list(self.active_providers)

        for prov in providers:
            try:
                prov.sync_turn(
                    user_content=user_content,
                    assistant_content=assistant_content,
                    session_id=session_id,
                    messages=messages,
                )
            except Exception as exc:
                logger.warning(f"Error in sync_turn for {prov.name}: {exc}")

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        with self._lock:
            providers = list(self.active_providers)

        schemas: List[Dict[str, Any]] = []
        seen_names = set()
        for prov in providers:
            try:
                for tool in prov.get_tool_schemas():
                    fn_name = tool.get("function", {}).get("name", "")
                    if fn_name and fn_name not in seen_names:
                        seen_names.add(fn_name)
                        schemas.append(tool)
            except Exception as exc:
                logger.warning(f"Error getting tools from {prov.name}: {exc}")
        return schemas

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        with self._lock:
            providers = list(self.active_providers)

        for prov in providers:
            try:
                tools = prov.get_tool_schemas()
                names = [t.get("function", {}).get("name") for t in tools]
                if tool_name in names:
                    return prov.handle_tool_call(tool_name, args)
            except Exception as exc:
                logger.warning(f"Error handling tool {tool_name} in {prov.name}: {exc}")

        return json.dumps({"error": f"No active provider handles tool {tool_name}"})

    def shutdown_all(self) -> None:
        with self._lock:
            providers = list(self.active_providers)
            self.active_providers.clear()
            self.primary_provider = None

        for prov in providers:
            try:
                prov.shutdown()
            except Exception as exc:
                logger.warning(f"Error shutting down {prov.name}: {exc}")
