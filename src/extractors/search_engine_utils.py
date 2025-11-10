thonimport logging
from dataclasses import dataclass
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str | None = None

def build_search_query(company_name: str) -> str:
    return f"linkedin of {company_name}".strip()

def _duckduckgo_search(
    query: str,
    settings: Dict[str, Any],
) -> List[SearchResult]:
    """
    Perform a DuckDuckGo HTML search and parse results.

    This uses the HTML endpoint which does not require an API key.
    """
    base_url = "https://duckduckgo.com/html/"
    params = {"q": query}
    headers = {
        "User-Agent": settings.get(
            "user_agent", "LinkedInCompanyFinder/1.0"
        )
    }
    timeout = float(settings.get("request_timeout", 10))

    try:
        resp = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Search request failed for query %s: %s", query, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results: List[SearchResult] = []

    # DuckDuckGo HTML layout: links with class 'result__a'
    for result in soup.select("a.result__a"):
        title = result.get_text(strip=True)
        url = result.get("href", "")
        if not url:
            continue

        snippet_elem = result.find_parent("div", class_="result")
        snippet_text = None
        if snippet_elem:
            snippet_span = snippet_elem.select_one(".result__snippet")
            if snippet_span:
                snippet_text = snippet_span.get_text(" ", strip=True)

        results.append(SearchResult(title=title, url=url, snippet=snippet_text))

        if len(results) >= int(settings.get("results_per_query", 10)):
            break

    logger.debug("Parsed %d results for query %s", len(results), query)
    return results

def search_company_results(
    company_name: str,
    settings: Dict[str, Any],
) -> List[SearchResult]:
    """
    High-level search function that chooses the search engine based on settings.

    Currently supports: duckduckgo
    """
    engine = str(settings.get("search_engine", "duckduckgo")).lower()
    query = build_search_query(company_name)

    logger.info("Running search for company '%s' via %s", company_name, engine)

    if engine == "duckduckgo":
        return _duckduckgo_search(query, settings)

    logger.warning(
        "Unknown search engine '%s'. Falling back to DuckDuckGo.",
        engine,
    )
    return _duckduckgo_search(query, settings)