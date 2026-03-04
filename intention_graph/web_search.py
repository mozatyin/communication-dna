"""Web search utilities for game research. No API key required.

Uses duckduckgo-search (optional) and httpx (already installed via anthropic).
If duckduckgo-search is not installed, search_game returns [].
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single web search result."""
    title: str
    snippet: str
    url: str


def search_game(query: str, max_results: int = 8) -> list[SearchResult]:
    """Search DuckDuckGo for game info. Returns [] if duckduckgo-search not installed."""
    try:
        from duckduckgo_search import DDGS  # type: ignore[import-untyped]
    except ImportError:
        return []

    results: list[SearchResult] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(f"{query} game design mechanics", max_results=max_results):
                results.append(SearchResult(
                    title=r.get("title", ""),
                    snippet=r.get("body", ""),
                    url=r.get("href", ""),
                ))
    except Exception:
        pass
    return results


def fetch_wikipedia(game_name: str, lang: str = "en") -> str | None:
    """Fetch Wikipedia summary for a game. Returns None on failure."""
    try:
        import httpx
    except ImportError:
        return None

    api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{game_name}"
    try:
        resp = httpx.get(api_url, timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("extract", None)
    except Exception:
        pass
    return None


def research_game(game_name: str, language: str = "en") -> str:
    """Aggregate DDG + Wikipedia into a single text block for LLM context.

    Returns combined research text, or empty string if no results found.
    """
    parts: list[str] = []

    # Wikipedia (try both English and Chinese if language is zh)
    wiki_langs = ["en"]
    if language.startswith("zh"):
        wiki_langs = ["zh", "en"]

    for lang in wiki_langs:
        summary = fetch_wikipedia(game_name, lang=lang)
        if summary:
            parts.append(f"[Wikipedia ({lang})]\n{summary}")
            break

    # DuckDuckGo search
    results = search_game(game_name)
    if results:
        snippets = [f"- {r.title}: {r.snippet}" for r in results[:6]]
        parts.append("[Web Search]\n" + "\n".join(snippets))

    return "\n\n".join(parts)
