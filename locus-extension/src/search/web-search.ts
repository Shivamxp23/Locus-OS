/**
 * SPEC §15.1 lines 2713-2719:
 * Web Search (8 Providers) Client & TypeScript Contracts (F-0105 / US-77).
 *
 * Multi-provider search and full content fetch client supporting:
 * OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini, Full Content Fetch.
 */

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  provider: string;
  content?: string;
}

export interface SearchOptions {
  max_results?: number;
  provider?: string;
}

export interface SearchQueryResponse {
  status: string;
  query: string;
  provider: string;
  results: SearchResult[];
}

export interface FetchResult {
  status: string;
  url: string;
  title?: string;
  content?: string;
  provider: string;
  message?: string;
}

export interface WebSearchProvidersInfo {
  status: string;
  providers: string[];
  available_providers: string[];
  active_provider: string;
}

export class WebSearchClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8000") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async search(
    query: string,
    options?: SearchOptions
  ): Promise<SearchResult[]> {
    const url = `${this.baseUrl}/search/query`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        max_results: options?.max_results ?? 5,
        provider: options?.provider,
      }),
    });
    if (resp.status === 503) {
      throw new Error("Web search is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to execute web search: ${resp.status}`);
    }
    const data = (await resp.json()) as SearchQueryResponse;
    return data.results || [];
  }

  async fetchContent(urlToFetch: string): Promise<FetchResult> {
    const url = `${this.baseUrl}/search/fetch`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlToFetch }),
    });
    if (resp.status === 503) {
      throw new Error("Web search is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to fetch content: ${resp.status}`);
    }
    return (await resp.json()) as FetchResult;
  }

  async getProviders(): Promise<WebSearchProvidersInfo> {
    const url = `${this.baseUrl}/search/providers`;
    const resp = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (resp.status === 503) {
      throw new Error("Web search is disabled by off-switch");
    }
    if (!resp.ok) {
      throw new Error(`Failed to get web search providers: ${resp.status}`);
    }
    return (await resp.json()) as WebSearchProvidersInfo;
  }
}
