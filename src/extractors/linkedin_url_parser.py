thonimport logging
import re
from difflib import SequenceMatcher
from typing import Iterable, Tuple

from .search_engine_utils import SearchResult

logger = logging.getLogger(__name__)

def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _is_linkedin_company_url(url: str) -> bool:
    url = url.lower()
    if "linkedin.com" not in url:
        return False
    # Basic patterns for company pages
    return "/company/" in url or "linkedin.com/company" in url

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def select_best_linkedin_company_url(
    search_results: Iterable[SearchResult],
    company_name: str,
) -> Tuple[str | None, SearchResult | None]:
    """
    Choose the most likely official LinkedIn company URL.

    Strategy:
    - Only consider results pointing to linkedin.com/company.
    - Score each candidate based on similarity between normalized company
      name and both the title and the path portion in the URL.
    - Return the URL with the highest score.
    """
    norm_company = _normalize_text(company_name)
    best_score = 0.0
    best_url: str | None = None
    best_result: SearchResult | None = None

    for result in search_results:
        url = result.url
        if not _is_linkedin_company_url(url):
            logger.debug("Skipping non-company LinkedIn URL: %s", url)
            continue

        norm_title = _normalize_text(result.title) if result.title else ""
        score_title = _similarity(norm_company, norm_title) if norm_title else 0.0

        # Extract company slug from URL, e.g., /company/tesla-motors/
        match = re.search(r"/company/([^/?#]+)/?", url.lower())
        company_slug = match.group(1) if match else ""
        norm_slug = _normalize_text(company_slug)
        score_slug = _similarity(norm_company, norm_slug) if norm_slug else 0.0

        score = max(score_title, score_slug)
        logger.debug(
            "Candidate URL=%s | title score=%.3f | slug score=%.3f | final=%.3f",
            url,
            score_title,
            score_slug,
            score,
        )

        if score > best_score:
            best_score = score
            best_url = url
            best_result = result

    if best_url:
        logger.info(
            "Selected LinkedIn URL '%s' for company '%s' with score %.3f",
            best_url,
            company_name,
            best_score,
        )
    else:
        logger.warning(
            "No suitable LinkedIn company URL found for '%s'", company_name
        )

    return best_url, best_result