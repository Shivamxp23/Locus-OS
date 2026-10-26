# US-77 Spec Traceability Matrix

## Feature
- ID: F-0105
- Title: Web Search (8 Providers)
- Spec Reference: §15.1 lines 2713-2719

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| Scope: OpenAI Search Provider | 2715 | `sidecar/search/providers.py:OpenAISearchProvider` | `tests/unit/test_web_search.py:test_openai_and_brave_search_providers` |
| Scope: Brave Search Provider | 2715 | `sidecar/search/providers.py:BraveSearchProvider` | `tests/unit/test_web_search.py:test_openai_and_brave_search_providers`, `tests/integration/test_web_search_service.py:test_service_search_query_specific_provider` |
| Scope: Parallel Search Provider | 2715 | `sidecar/search/providers.py:ParallelSearchProvider` | `tests/unit/test_web_search.py:test_parallel_tavily_exa_providers` |
| Scope: Tavily Search Provider | 2715 | `sidecar/search/providers.py:TavilySearchProvider` | `tests/unit/test_web_search.py:test_parallel_tavily_exa_providers` |
| Scope: Exa Search Provider | 2715 | `sidecar/search/providers.py:ExaSearchProvider` | `tests/unit/test_web_search.py:test_parallel_tavily_exa_providers` |
| Scope: Perplexity Search Provider | 2715 | `sidecar/search/providers.py:PerplexitySearchProvider` | `tests/unit/test_web_search.py:test_perplexity_gemini_content_fetch_providers` |
| Scope: Gemini Search Provider | 2715 | `sidecar/search/providers.py:GeminiSearchProvider` | `tests/unit/test_web_search.py:test_perplexity_gemini_content_fetch_providers` |
| Scope: Full Content Fetch Provider | 2715 | `sidecar/search/providers.py:FullContentFetchProvider` | `tests/unit/test_web_search.py:test_perplexity_gemini_content_fetch_providers`, `tests/integration/test_web_search_service.py:test_service_search_fetch` |
| Provider Interface & Manager with runtime routing | 2715 | `sidecar/search/manager.py:WebSearchManager` | `tests/unit/test_web_search.py:test_web_search_manager_registration_and_dispatch`, `test_web_search_manager_set_provider` |
| Modular Off-switches (`locus.web_search_8_providers.enabled`, `locus.web_search.enabled`) returning HTTP 503 | 2714 | `sidecar/providers/web_search.py:DefaultWebSearchProvider`, `sidecar/service.py` | `tests/unit/test_web_search.py:test_web_search_provider_modular_off_switches`, `tests/integration/test_web_search_service.py:test_service_search_off_switches` |
| FastAPI Service Routes (`/search/query`, `/search/fetch`, `/search/providers`) | 2715 | `sidecar/service.py` | `tests/integration/test_web_search_service.py` |
| Extension Client Contract | 2715 | `locus-extension/src/search/web-search.ts:WebSearchClient` | TypeScript contract and client |
