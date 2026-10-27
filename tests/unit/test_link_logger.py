"""
Unit tests for Link Dump & Web Resource Logger (F-0062 / US-99).
"""
from pathlib import Path
import pytest
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.ingestion.link_logger import (
    LinkDumpLogger,
    LinkResourceSummary,
    ProcessLinkDumpResult,
    extract_readable_text,
    slugify,
)
from sidecar.providers.link_logger import (
    BaseLinkDumpLoggerProvider,
    DefaultLinkDumpLoggerProvider,
)


def test_slugify_and_readable_text_extraction():
    """
    SPEC §27.6 line 7273: "clean_article = extract_readable_text(html)  // Trafilatura / Readability"
    """
    html_sample = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Advances in Deep Learning Architectures</title>
        <style>.nav { color: red; }</style>
      </head>
      <body>
        <nav><a href="/">Home</a></nav>
        <h1>Neural Scaling Laws and Transformers</h1>
        <p>Recent experiments demonstrate remarkable sample efficiency in modern LLM reasoning models.</p>
        <p>Transformer architectures continue to demonstrate power-law scaling across diverse multimodal benchmarks.</p>
        <script>console.log("analytics");</script>
      </body>
    </html>
    """
    title, text = extract_readable_text(html_sample)
    assert title == "Advances in Deep Learning Architectures"
    assert "Neural Scaling Laws" in text
    assert "console.log" not in text
    assert ".nav {" not in text
    assert slugify(title) == "advances-in-deep-learning-architectures"


def test_domain_classification_across_categories():
    """
    SPEC §27.6 line 7284: "- domain_category: (ai_research | systems_engineering | film_production | health_longevity)"
    """
    logger = LinkDumpLogger()

    ai_text = "Transformers, Claude, Gemini, and LLM inference benchmark analysis."
    assert logger.classify_domain(ai_text) == "ai_research"

    sys_text = "Docker containerization with Kubernetes and FastAPI sidecar architecture."
    assert logger.classify_domain(sys_text) == "systems_engineering"

    film_text = "Cinematography lighting techniques, RED camera rigs, and video editing workflow."
    assert logger.classify_domain(film_text) == "film_production"

    health_text = "Zone 2 cardio training, sleep hygiene, and intermittent fasting for longevity."
    assert logger.classify_domain(health_text) == "health_longevity"


def test_synthesize_exactly_three_takeaways():
    """
    SPEC §27.6 line 7285: "- key_takeaways: [3 bullet points]"
    """
    logger = LinkDumpLogger()
    content = (
        "First insight demonstrates high throughput parallel computation. "
        "Second observation proves memory bandwidth saturation is critical. "
        "Third finding reveals quantization reduces latency without degradation. "
        "Fourth point is supplementary information."
    )
    takeaways = logger.synthesize_takeaways(content, "Computation Efficiency")
    assert len(takeaways) == 3
    assert all(len(t) > 10 for t in takeaways)


def test_relevance_assessment_and_user_commentary():
    """
    SPEC §27.6 line 7286: "- relevance_to_goals: How this connects to active projects"
    """
    logger = LinkDumpLogger()

    relevance_with_comment = logger.assess_relevance("systems_engineering", "Need this for Locus sidecar scaling")
    assert "Need this for Locus sidecar scaling" in relevance_with_comment
    assert "systems engineering" in relevance_with_comment

    relevance_default = logger.assess_relevance("ai_research", "")
    assert "cognitive operating system" in relevance_default


def test_markdown_rendering_and_frontmatter():
    """
    SPEC §27.6 line 7291: "note_md = format_resource_markdown(url, summary_data, user_commentary)"
    """
    resource = LinkResourceSummary(
        url="https://arxiv.org/abs/2401.00000",
        title="DeepSeek R1 Architecture",
        domain_category="ai_research",
        key_takeaways=[
            "Reinforcement learning boosts math reasoning.",
            "Cold start data can be distilled efficiently.",
            "Long context verification enhances coherence.",
        ],
        relevance_to_goals="Directly informs Locus reasoning engines.",
        user_commentary="Crucial paper for prompt reasoning",
        excerpt="Abstract: Large reasoning models trained with pure RL...",
    )

    md = resource.to_markdown()
    assert md.startswith("---")
    assert 'title: "DeepSeek R1 Architecture"' in md
    assert 'domain_category: "ai_research"' in md
    assert 'tags: ["#resource", "#ai_research"]' in md
    assert "# DeepSeek R1 Architecture" in md
    assert "https://arxiv.org/abs/2401.00000" in md
    assert "Crucial paper for prompt reasoning" in md
    assert "## Key Takeaways" in md
    assert "- Reinforcement learning boosts math reasoning." in md
    assert "## Relevance to Goals" in md
    assert "## Excerpt" in md


def test_vault_persistence_resources_category(tmp_path):
    """
    SPEC §27.6 line 7290: "note_path = f\"/vault/03-Resources/{summary_data.domain_category}/{slugify(summary_data.title)}.md\""
    """
    logger = LinkDumpLogger()
    html_doc = """
    <html>
      <head><title>FastAPI Performance Optimization</title></head>
      <body>
        <h1>FastAPI and Uvicorn Tuning</h1>
        <p>Optimizing async worker processes improves HTTP latency significantly.</p>
        <p>Using orjson serialization accelerates JSON payload response generation.</p>
        <p>Connection pooling ensures persistent database throughput under load.</p>
      </body>
    </html>
    """

    res = logger.process_link_dump(
        url="https://fastapi.tiangolo.com/advanced/performance/",
        user_commentary="Useful for sidecar latency tuning",
        html_content=html_doc,
        save_to_vault=True,
        vault_root=tmp_path,
    )

    assert res.status == "SAVED"
    assert res.path is not None
    assert Path(res.path).exists()
    assert "03-Resources" in res.path
    assert "systems_engineering" in res.path
    assert res.path.endswith("fastapi-performance-optimization.md")

    content = Path(res.path).read_text(encoding="utf-8")
    assert 'domain_category: "systems_engineering"' in content
    assert "Useful for sidecar latency tuning" in content


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.6 line 7265: "Intercepts raw URLs sent to Telegram/chat, scrapes article content"
    """
    logger = LinkDumpLogger()
    switch = logger.SWITCH_KEY

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert logger.is_enabled() is False

    res = logger.process_link_dump("https://example.com")
    assert res.status == "DISABLED"
    assert "disabled" in (res.error or "").lower()


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.6 line 7265: "Registers as a provider in sidecar/providers/ with modular off-switch locus.link_dump_logger.enabled returning 503."
    """
    provider = DefaultLinkDumpLoggerProvider()
    switch = "locus.link_dump_logger.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_proc = provider.process_link("https://example.com")
    assert res_proc.get("status_code") == 503
    assert res_proc.get("disabled") == switch

    res_status = provider.get_status()
    assert res_status.get("status_code") == 503
    assert res_status.get("disabled") == switch


def test_provider_swap_polymorphism():
    """
    SPEC §27.6 line 7265: "Registers as a provider in sidecar/providers/ with modular off-switch locus.link_dump_logger.enabled returning 503."
    """
    class MockLinkDumpLoggerProvider(BaseLinkDumpLoggerProvider):
        @property
        def name(self) -> str:
            return "mock_link_logger"

        def is_feature_enabled(self):
            return True, "mock.switch"

        def process_link(self, url, user_commentary="", html_content=None, save_to_vault=True, vault_root=None):
            return {"status_code": 200, "status": "SAVED", "path": "/mock/resource.md", "takeaways": ["T1", "T2", "T3"]}

        def get_status(self):
            return {"status_code": 200, "mock": True}

    provider: BaseLinkDumpLoggerProvider = MockLinkDumpLoggerProvider()
    assert provider.name == "mock_link_logger"
    res = provider.process_link("https://example.org")
    assert res["status_code"] == 200
    assert len(res["takeaways"]) == 3
