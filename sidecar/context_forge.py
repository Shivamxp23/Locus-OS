"""
SPEC §2.5 / F-0094 / US-34: Context Forge (Stage 6) — The 6-Layer Assembler Implementation.
Implements parallel retrieval consolidation, global relevance scoring, 6-layer budgeting,
Headroom CCR compression fallback, Hebbian edge increment, and anti-hallucination prepending.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta
import logging
import math
import time
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.providers.context_forge import (
    ANTI_HALLUCINATION_INSTRUCTION,
    AssembledLayer,
    BaseContextForgeProvider,
    ContextForgeResult,
    LOCUS_SHORTHAND_DICTIONARY,
    LayerBudgetConfig,
    RetrievalInput,
    SOURCE_PRIORITIES,
)

logger = logging.getLogger("sidecar.context_forge")

SYSTEM_IDENTITY_PROMPT: str = (
    "You are Locus OS, a personal cognitive operating system aligned with the user's "
    "core life goals, circadian capacity, and behavioral directives."
)


def estimate_tokens(text: str) -> int:
    """Robust character-to-token approximation (max(1, len(text) // 4))."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text preserving word boundaries within token budget."""
    if not text or max_tokens <= 0:
        return ""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip()


class ContextForgeProvider(BaseContextForgeProvider):
    """
    Default Context Forge provider implementing the 12-step assembly logic.
    """

    def __init__(self) -> None:
        pass

    def is_enabled(self) -> bool:
        """
        Modular off-switch per §2.5 Adaptation to Locus Architecture.
        Checks locus.brain.context_forge.enabled (default: true) or locus.context_forge.enabled.
        """
        val = config.get("locus.brain.context_forge.enabled")
        if val is None:
            val = config.get("locus.context_forge.enabled", True)
        return bool(val)

    def get_layer_budget_config(self) -> LayerBudgetConfig:
        """Read layer budget configuration from config."""
        cfg_dict = config.get("locus.brain.context_forge.layers") or {}
        return LayerBudgetConfig.from_dict(cfg_dict)

    def calculate_recency_weight(self, age_seconds: float) -> float:
        """
        SPEC §2.5 STEP 2:
        Recency weight: last 6h = 1.0, last 24h = 0.8, last 7d = 0.5, older = 0.2.
        """
        if age_seconds <= 6 * 3600:
            return 1.0
        elif age_seconds <= 24 * 3600:
            return 0.8
        elif age_seconds <= 7 * 86400:
            return 0.5
        else:
            return 0.2

    def get_source_priority(self, source_type: str) -> float:
        """
        SPEC §2.5 STEP 2:
        Source priority: Neo4j pathways (0.4) > PG facts (0.3) > pgvector (0.2) > Web (0.1).
        """
        key = source_type.lower().strip()
        return SOURCE_PRIORITIES.get(key, 0.1)

    def calculate_relevance_score(
        self,
        semantic_similarity: float,
        recency_weight: float,
        source_priority: float,
    ) -> float:
        """
        SPEC §2.5 STEP 2:
        Unified Score = (semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)
        """
        sem = max(0.0, min(1.0, float(semantic_similarity)))
        rec = max(0.0, min(1.0, float(recency_weight)))
        src = max(0.0, min(1.0, float(source_priority)))
        return round((sem * 0.6) + (rec * 0.25) + (src * 0.15), 4)

    def _assemble_layer_1_identity(self, identity: Dict[str, Any], limit: int) -> AssembledLayer:
        """
        SPEC §2.5 STEP 3: Layer 1 — User Identity (Hard limit: 80 tokens)
        Inject stated life goals, active factions, confirmed behavioral tendencies, peak performance windows.
        """
        parts = []
        if identity.get("life_goals"):
            goals = identity["life_goals"]
            if isinstance(goals, list):
                goals = "; ".join(str(g) for g in goals)
            parts.append(f"Goals: {goals}")
        if identity.get("active_factions"):
            factions = identity["active_factions"]
            if isinstance(factions, list):
                factions = ", ".join(str(f) for f in factions)
            parts.append(f"Factions: {factions}")
        if identity.get("behavioral_tendencies"):
            tendencies = identity["behavioral_tendencies"]
            if isinstance(tendencies, list):
                tendencies = "; ".join(str(t) for t in tendencies)
            parts.append(f"Tendencies: {tendencies}")
        if identity.get("peak_performance_windows"):
            windows = identity["peak_performance_windows"]
            if isinstance(windows, list):
                windows = ", ".join(str(w) for w in windows)
            parts.append(f"Peak: {windows}")

        raw_text = " | ".join(parts) if parts else "Identity: Standard Baseline"
        content = truncate_to_tokens(raw_text, limit)
        return AssembledLayer(
            layer_num=1,
            name="User Identity",
            content=content,
            token_count=estimate_tokens(content),
        )

    def _assemble_layer_2_temporal(self, temporal: Dict[str, Any], limit: int) -> AssembledLayer:
        """
        SPEC §2.5 STEP 4: Layer 2 — Temporal Context (Hard limit: 60 tokens)
        Inject current time (IST), operating_mode, DCS, day of week, active exam flags.
        """
        # IST is UTC+5:30
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        ts = temporal.get("timestamp") or time.time()
        dt_ist = datetime.fromtimestamp(ts, tz=ist_tz)
        formatted_time = dt_ist.strftime("%Y-%m-%d %H:%M IST")
        day_of_week = dt_ist.strftime("%A")

        op_mode = temporal.get("operating_mode", "NORMAL")
        dcs = temporal.get("dcs", 5.0)
        exam_flags = temporal.get("active_exam_flags")
        if isinstance(exam_flags, list):
            exam_flags_str = ", ".join(str(e) for e in exam_flags)
        else:
            exam_flags_str = str(exam_flags) if exam_flags else "None"

        raw_text = (
            f"Time: {formatted_time} ({day_of_week}) | Mode: {op_mode} | "
            f"DCS: {dcs} | Exam Flags: {exam_flags_str}"
        )
        content = truncate_to_tokens(raw_text, limit)
        return AssembledLayer(
            layer_num=2,
            name="Temporal Context",
            content=content,
            token_count=estimate_tokens(content),
        )

    def _assemble_layer_3_events(self, events: List[Dict[str, Any]], limit: int) -> AssembledLayer:
        """
        SPEC §2.5 STEP 5: Layer 3 — PostgreSQL Events (Hard limit: 180 tokens)
        Inject recent events compressed via LOCUS_SHORTHAND (e.g. {✓:task_name,dur:45,q:8}).
        """
        if not events:
            return AssembledLayer(
                layer_num=3,
                name="PostgreSQL Events",
                content="",
                token_count=0,
            )

        event_shorthands = []
        for ev in events:
            # Format shorthand
            task = ev.get("task") or ev.get("name") or "unnamed"
            dur = ev.get("dur") or ev.get("duration", 0)
            q = ev.get("q") or ev.get("quality", 5)
            shorthand = f"{{✓:{task},dur:{dur},q:{q}}}"
            event_shorthands.append(shorthand)

        raw_text = "Events: " + " ".join(event_shorthands)
        content = truncate_to_tokens(raw_text, limit)
        return AssembledLayer(
            layer_num=3,
            name="PostgreSQL Events",
            content=content,
            token_count=estimate_tokens(content),
        )

    def _assemble_layer_4_neo4j(
        self, neo4j_paths: List[Dict[str, Any]], limit: int
    ) -> Tuple[AssembledLayer, List[Dict[str, Any]]]:
        """
        SPEC §2.5 STEP 6: Layer 4 — Neo4j Pathways (Hard limit: 150 tokens)
        Inject Neo4j paths with edge weight > 0.3. Format: 'task_A → behavior_B (w:0.84) → outcome_C'.
        SPEC §2.5 STEP 10: Hebbian Weight Increment (+0.1)
        For every Neo4j path included in Layer 4, increment edge weights by +0.1 in Neo4j.
        """
        included_paths = []
        hebbian_updates = []
        path_strings = []

        for p in neo4j_paths:
            w = float(p.get("weight", p.get("edge_weight", 0.0)))
            if w <= 0.3:
                continue

            # Format path
            formatted = p.get("path_str")
            if not formatted:
                from_node = p.get("from_node", "A")
                rel = p.get("relation", "rel")
                to_node = p.get("to_node", "B")
                outcome = p.get("outcome")
                if outcome:
                    formatted = f"{from_node} → {rel} (w:{w:.2f}) → {outcome}"
                else:
                    formatted = f"{from_node} → {to_node} (w:{w:.2f})"

            # Check token budget before appending
            candidate_text = "Pathways: " + " | ".join(path_strings + [formatted])
            if estimate_tokens(candidate_text) > limit:
                break

            path_strings.append(formatted)
            included_paths.append(p)
            new_weight = round(min(1.0, w + 0.1), 2)
            hebbian_updates.append({
                "path": formatted,
                "old_weight": w,
                "new_weight": new_weight,
            })

        raw_text = "Pathways: " + " | ".join(path_strings) if path_strings else ""
        content = truncate_to_tokens(raw_text, limit)
        layer = AssembledLayer(
            layer_num=4,
            name="Neo4j Pathways",
            content=content,
            token_count=estimate_tokens(content),
        )
        return layer, hebbian_updates

    def _assemble_layer_5_semantic(
        self, snippets: List[Dict[str, Any]], limit: int, now_ts: float
    ) -> AssembledLayer:
        """
        SPEC §2.5 STEP 7: Layer 5 — pgvector / Obsidian Semantic (Hard limit: 200 tokens)
        Inject top semantic snippets with recency boost multiplier (×1.5 for last 7d vectors).
        """
        if not snippets:
            return AssembledLayer(
                layer_num=5,
                name="pgvector / Semantic",
                content="",
                token_count=0,
            )

        scored_snippets = []
        for s in snippets:
            text = s.get("text", "")
            sim = float(s.get("similarity", s.get("semantic_similarity", 0.5)))
            ts = float(s.get("timestamp", now_ts))
            age = max(0.0, now_ts - ts)
            rec_weight = self.calculate_recency_weight(age)

            # Recency boost multiplier (x1.5 for last 7d vectors per STEP 7)
            if age <= 7 * 86400:
                rec_weight = min(1.0, rec_weight * 1.5)

            score = self.calculate_relevance_score(
                semantic_similarity=sim,
                recency_weight=rec_weight,
                source_priority=self.get_source_priority("pgvector"),
            )
            scored_snippets.append((score, text))

        # Sort by score descending
        scored_snippets.sort(key=lambda x: x[0], reverse=True)

        selected_texts = []
        for score, text in scored_snippets:
            candidate_text = "Semantic: " + " ; ".join(selected_texts + [text])
            if estimate_tokens(candidate_text) > limit:
                # If even first doesn't fit, truncate it
                if not selected_texts:
                    selected_texts.append(truncate_to_tokens(text, limit - 5))
                break
            selected_texts.append(text)

        raw_text = "Semantic: " + " ; ".join(selected_texts) if selected_texts else ""
        content = truncate_to_tokens(raw_text, limit)
        return AssembledLayer(
            layer_num=5,
            name="pgvector / Semantic",
            content=content,
            token_count=estimate_tokens(content),
        )

    def _assemble_layer_6_web(
        self,
        web_results: List[Dict[str, Any]],
        limit: int,
        intent_requires_web: bool,
        has_other_retrievals: bool,
    ) -> AssembledLayer:
        """
        SPEC §2.5 STEP 8: Layer 6 — Web Search Results (Hard limit: 0 - 100 tokens)
        Populated ONLY if intent requires external knowledge or retrieval returned empty. Top 3 snippets.
        """
        should_populate = intent_requires_web or (not has_other_retrievals)
        if not should_populate or not web_results:
            return AssembledLayer(
                layer_num=6,
                name="Web Search Results",
                content="",
                token_count=0,
            )

        top_3 = web_results[:3]
        snippets = []
        for res in top_3:
            snip = res.get("snippet") or res.get("text") or res.get("title", "")
            if snip:
                snippets.append(snip)

        raw_text = "Web: " + " | ".join(snippets) if snippets else ""
        content = truncate_to_tokens(raw_text, limit)
        return AssembledLayer(
            layer_num=6,
            name="Web Search Results",
            content=content,
            token_count=estimate_tokens(content),
        )

    def assemble_context(
        self,
        retrieval_input: RetrievalInput,
        budget_override: Optional[LayerBudgetConfig] = None,
    ) -> ContextForgeResult:
        """
        SPEC §2.5 Context Forge (Stage 6) 12-Step Assembly.
        """
        if not self.is_enabled():
            raise RuntimeError("Context Forge is disabled by configuration (503).")

        now_ts = time.time()
        budgets = budget_override or self.get_layer_budget_config()

        # STEP 1 & 2 & 3: Layer 1 User Identity
        l1 = self._assemble_layer_1_identity(retrieval_input.identity, budgets.identity_limit)

        # STEP 4: Layer 2 Temporal Context
        l2 = self._assemble_layer_2_temporal(retrieval_input.temporal, budgets.temporal_limit)

        # STEP 5: Layer 3 PostgreSQL Events
        l3 = self._assemble_layer_3_events(retrieval_input.events, budgets.events_limit)

        # STEP 6 & 10: Layer 4 Neo4j Pathways + Hebbian Updates
        l4, hebbian_updates = self._assemble_layer_4_neo4j(
            retrieval_input.neo4j_paths, budgets.neo4j_limit
        )

        # STEP 7: Layer 5 pgvector / Obsidian Semantic
        l5 = self._assemble_layer_5_semantic(
            retrieval_input.semantic_snippets, budgets.semantic_limit, now_ts
        )

        # STEP 8: Layer 6 Web Search Results
        has_other = bool(
            retrieval_input.events
            or retrieval_input.neo4j_paths
            or retrieval_input.semantic_snippets
        )
        l6 = self._assemble_layer_6_web(
            retrieval_input.web_results,
            budgets.web_limit,
            retrieval_input.intent_requires_web,
            has_other,
        )

        # STEP 9: Token Budget Enforcement & Headroom Compression
        # Appends layers 1->6. If total exceeds 800 tokens, applies Headroom CCR compression to Layer 5 & 3.
        # Layers 1 & 2 are NEVER truncated.
        compression_applied = False
        all_layers = [l1, l2, l3, l4, l5, l6]
        total_tokens = sum(l.token_count for l in all_layers)

        if total_tokens > budgets.total_limit:
            compression_applied = True
            excess = total_tokens - budgets.total_limit

            # Compress Layer 5 (Semantic) first
            if l5.token_count > 0:
                reducible = l5.token_count
                reduction = min(reducible, excess)
                new_tokens = max(0, reducible - reduction)
                l5.content = truncate_to_tokens(l5.content, new_tokens)
                l5.token_count = estimate_tokens(l5.content)
                excess -= reduction

            # If still exceeding headroom, compress Layer 3 (PostgreSQL Events)
            if excess > 0 and l3.token_count > 0:
                reducible = l3.token_count
                reduction = min(reducible, excess)
                new_tokens = max(0, reducible - reduction)
                l3.content = truncate_to_tokens(l3.content, new_tokens)
                l3.token_count = estimate_tokens(l3.content)
                excess -= reduction

            # Recompute total tokens
            total_tokens = sum(l.token_count for l in all_layers)

        # STEP 11: System Prompt & LOCUS_SHORTHAND Prepend
        # Prepends identity system prompt + LOCUS_SHORTHAND decoder dictionary + strict anti-hallucination instruction:
        # "If data needed to answer a question is not in this context, say you don't have it yet. Do NOT invent data."
        active_layer_contents = [l.content for l in all_layers if l.content.strip()]
        context_body = "\n\n".join(active_layer_contents)

        assembled_prompt = (
            f"{SYSTEM_IDENTITY_PROMPT}\n\n"
            f"{LOCUS_SHORTHAND_DICTIONARY}\n\n"
            f"{ANTI_HALLUCINATION_INSTRUCTION}\n\n"
            f"--- BEGIN CONTEXT BLOCK ---\n"
            f"{context_body}\n"
            f"--- END CONTEXT BLOCK ---"
        )

        # STEP 12: Return Assembled Context Block
        metadata = {
            "total_layers": len(all_layers),
            "active_layers": len([l for l in all_layers if l.token_count > 0]),
            "timestamp": now_ts,
            "compression_applied": compression_applied,
            "headroom_budget": budgets.total_limit,
        }

        return ContextForgeResult(
            assembled_prompt=assembled_prompt,
            layers=all_layers,
            total_tokens=total_tokens,
            compression_applied=compression_applied,
            hebbian_updates=hebbian_updates,
            metadata=metadata,
        )


# Register default provider
get_registry().register("context_forge", "default", ContextForgeProvider)
