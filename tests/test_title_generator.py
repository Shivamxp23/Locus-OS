import pytest
from sidecar.title_generator import (
    clean_title,
    fallback_title,
    TitleGenerator,
)


def test_clean_title_removes_quotes_and_prefixes():
    assert clean_title('"Title: Building the Knowledge Graph."') == "Building the Knowledge Graph"
    assert clean_title("'Refactoring Neo4j client;'") == "Refactoring Neo4j client"
    long_t = "A" * 100
    cleaned_long = clean_title(long_t)
    assert len(cleaned_long) == 80
    assert cleaned_long.endswith("...")


def test_fallback_title():
    assert fallback_title("implement holographic HRR memory binding in python") == "Implement holographic hrr memory binding in"
    assert fallback_title("") == "New Session"


def test_title_generator_with_mock_llm():
    def mock_llm(messages):
        return ' "Title: Neural Plasticity Engine." '

    gen = TitleGenerator(llm_caller=mock_llm)
    res = gen.generate_title("What is STDP?", "STDP is spike-timing-dependent plasticity.")
    assert res == "Neural Plasticity Engine"


def test_title_generator_fallback_on_error():
    def failing_llm(messages):
        raise RuntimeError("API timeout")

    gen = TitleGenerator(llm_caller=failing_llm)
    res = gen.generate_title("Fixing rate limiter bug in sidecar")
    assert res == "Fixing rate limiter bug in sidecar"
