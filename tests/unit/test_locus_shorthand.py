"""
Unit tests for LOCUS_SHORTHAND 4× Text Compressor (F-0122 / US-96).
"""
import pytest
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.compression.shorthand import (
    SHORTHAND_DECODER_DICT,
    SHORTHAND_DICTIONARY,
    LocusShorthandCompressor,
    ShorthandCompressionResult,
)
from sidecar.providers.shorthand import (
    BaseShorthandCompressorProvider,
    DefaultShorthandCompressorProvider,
)


def test_shorthand_dictionary_substitution():
    """
    SPEC §27.3 line 7123: "SHORTHAND_DICTIONARY = [("because", "∵"), ("therefore", "∴"), ("approximately", "≈"), ("greater than", ">"), ("less than", "<"), ("and", "&"), ("with", "w/"), ("without", "w/o"), ("which", "wh/"), ("between", "b/w"), ("regarding", "re:"), ("for example", "e.g.")]"
    """
    compressor = LocusShorthandCompressor()

    sample = "We succeeded because of effort and therefore we won with team and without doubt."
    res = compressor.compress(sample, strip_articles=False)

    assert "∵" in res.compressed_text
    assert "∴" in res.compressed_text
    assert "&" in res.compressed_text
    assert "w/" in res.compressed_text
    assert "w/o" in res.compressed_text
    assert res.compressed is True
    assert res.tokens_saved > 0


def test_grammatical_article_stripping():
    r"""
    SPEC §27.3 line 7136: "Strip unambiguous grammatical articles: text = regex_replace(r" (the|a|an) \s+", "", text, case_insensitive=True)"
    """
    compressor = LocusShorthandCompressor()

    sample = "The quick brown fox jumps over a lazy dog near an apple."
    res = compressor.compress(sample, strip_articles=True)

    # The articles "the", "a", "an" followed by space must be stripped
    words = res.compressed_text.lower().split()
    assert "the" not in words
    assert "a" not in words
    assert "an" not in words
    assert "quick" in words
    assert "fox" in words
    assert "lazy" in words


def test_shorthand_decompression_expansion():
    """
    SPEC §27.3 line 7119: "Deterministic 4× regex compression pipeline reducing prompt token consumption"
    """
    compressor = LocusShorthandCompressor()

    compressed = "task done ∵ high focus & good sleep ∴ success"
    expanded = compressor.decompress(compressed)

    assert "because" in expanded
    assert "therefore" in expanded
    assert "and" in expanded


def test_behavioral_event_compression():
    """
    SPEC §27.3 line 7148: "Applied to Context Forge Layer 3 (PostgreSQL Events) and Layer 4 (Neo4j Pathways) before token budget checking."
    """
    compressor = LocusShorthandCompressor()

    # Task completion
    ev_comp = compressor.compress_event(
        "task_completion",
        {"task": "Build Shorthand", "dur": 45, "q": 8},
    )
    assert ev_comp == "{✓:Build_Shorthand,dur:45,q:8}"

    # Deferral
    ev_def = compressor.compress_event(
        "deferral",
        {"task": "Write Documentation", "n": 3, "r": "tired"},
    )
    assert ev_def == "{→:Write_Documentation,n:3,r:tired}"

    # Checkin
    ev_chk = compressor.compress_event(
        "checkin",
        {"e": 7, "m": 6, "s": 3, "sl": 7},
    )
    assert ev_chk == "{e:7,m:6,s:3,sl:7}"


def test_decoder_dictionary_export():
    """
    SPEC §27.3 line 7123: "SHORTHAND_DICTIONARY = [("because", "∵"), ("therefore", "∴"), ("approximately", "≈"), ("greater than", ">"), ("less than", "<"), ("and", "&"), ("with", "w/"), ("without", "w/o"), ("which", "wh/"), ("between", "b/w"), ("regarding", "re:"), ("for example", "e.g.")]"
    """
    compressor = LocusShorthandCompressor()
    decoder = compressor.get_decoder_dictionary()

    assert decoder["∵"] == "because"
    assert decoder["∴"] == "therefore"
    assert decoder["&"] == "and"
    assert decoder["w/"] == "with"
    assert decoder["w/o"] == "without"
    assert len(decoder) >= 12


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.3 line 7119: "Deterministic 4× regex compression pipeline reducing prompt token consumption"
    """
    compressor = LocusShorthandCompressor()
    switch = compressor.SWITCH_KEY

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert compressor.is_shorthand_enabled() is False

    raw = "The work was good because and therefore we celebrated."
    res = compressor.compress(raw)
    assert res.compressed is False
    assert res.compressed_text == raw
    assert res.compression_ratio == 1.0


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.3 line 7119: "Registers as a provider in sidecar/providers/ with modular off-switch locus.locus_shorthand_4_text_compressor.enabled returning 503."
    """
    provider = DefaultShorthandCompressorProvider()
    switch = "locus.locus_shorthand_4_text_compressor.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_comp = provider.compress("test text")
    assert res_comp.get("status_code") == 503

    res_dec = provider.decompress("test text")
    assert res_dec.get("status_code") == 503

    res_ev = provider.compress_event("checkin", {})
    assert res_ev.get("status_code") == 503

    res_dict = provider.get_decoder_dictionary()
    assert res_dict.get("status_code") == 503

    res_st = provider.get_status()
    assert res_st.get("status_code") == 503


def test_provider_swap_polymorphism():
    """
    SPEC §27.3 line 7119: "Registers as a provider in sidecar/providers/ with modular off-switch locus.locus_shorthand_4_text_compressor.enabled returning 503."
    """
    class MockCustomShorthandProvider(BaseShorthandCompressorProvider):
        @property
        def name(self) -> str:
            return "mock_shorthand_provider"

        def is_feature_enabled(self) -> Tuple[bool, str]:
            return True, ""

        def compress(self, text: str, strip_articles: bool = True) -> Dict[str, Any]:
            return {"mock": True, "compressed": "custom"}

        def decompress(self, text: str) -> Dict[str, Any]:
            return {"mock": True, "decompressed": text}

        def compress_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
            return {"mock": True, "event": event_type}

        def get_decoder_dictionary(self) -> Dict[str, Any]:
            return {"mock": True, "decoder": {}}

        def get_status(self) -> Dict[str, Any]:
            return {"mock": True, "name": self.name}

    prov: BaseShorthandCompressorProvider = MockCustomShorthandProvider()
    assert prov.name == "mock_shorthand_provider"
    assert prov.compress("hello")["mock"] is True
    assert prov.decompress("custom")["mock"] is True
