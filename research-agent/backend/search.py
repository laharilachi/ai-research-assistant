"""DuckDuckGo web search integration using LangChain and ddgs.
Handles query execution, URL deduplication, and result formatting.
"""
import logging
import re
from urllib.parse import urlparse, urlunparse
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def clean_url(url: str) -> str:
    """Normalize a URL to prevent duplicate visits with minor param variations."""
    try:
        parsed = urlparse(url.strip())
        # Strip tracking queries if needed and trailing slashes
        clean_path = parsed.path.rstrip("/")
        return urlunparse((parsed.scheme, parsed.netloc.lower(), clean_path, "", "", ""))
    except Exception:
        return url.strip()


def search_single_query(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Executes a single DuckDuckGo search query using ddgs/LangChain utilities."""
    hits: List[Dict[str, str]] = []

    # Primary approach: ddgs / duckduckgo_search
    try:
        try:
            from ddgs import DDGS
            ddg = DDGS()
        except ImportError:
            from duckduckgo_search import DDGS
            ddg = DDGS()

        raw_results = list(ddg.text(query, max_results=max_results))
        for item in raw_results:
            title = item.get("title", "").strip()
            url = item.get("href") or item.get("link") or ""
            snippet = item.get("body") or item.get("snippet") or ""
            if url and (title or snippet):
                hits.append({
                    "title": title or "Untitled Source",
                    "url": url.strip(),
                    "snippet": snippet.strip(),
                })
        if hits:
            return hits
    except Exception as e:
        logger.warning(f"Direct DDGS search failed for '{query}': {e}. Trying LangChain wrapper fallback...")

    # Fallback approach: LangChain DuckDuckGoSearchAPIWrapper
    try:
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
        wrapper = DuckDuckGoSearchAPIWrapper(max_results=max_results)
        lc_results = wrapper.results(query, max_results=max_results)
        for item in lc_results:
            hits.append({
                "title": item.get("title", "Untitled Source").strip(),
                "url": item.get("link", "").strip(),
                "snippet": item.get("snippet", "").strip(),
            })
    except Exception as e:
        logger.error(f"LangChain DuckDuckGo fallback also failed for '{query}': {e}")

    return hits


def search_multiple_queries(queries: List[str], max_total_sources: int = 8) -> List[Dict[str, str]]:
    """Runs web search across multiple queries and aggregates unique, high-quality sources.
    
    Args:
        queries: List of 4-6 search queries.
        max_total_sources: Maximum number of distinct URLs to retain.
        
    Returns:
        List of dicts: [{'title': ..., 'url': ..., 'snippet': ...}]
    """
    seen_urls = set()
    aggregated_sources: List[Dict[str, str]] = []

    # Filter out common video/file domains that cannot be parsed by trafilatura
    ignored_patterns = [
        r"youtube\.com",
        r"youtu\.be",
        r"\.pdf($|\?)",
        r"\.docx?($|\?)",
        r"twitter\.com",
        r"x\.com",
        r"facebook\.com",
        r"instagram\.com",
    ]

    for q in queries:
        results = search_single_query(q, max_results=3)
        for r in results:
            url = r["url"]
            if not url or not url.startswith("http"):
                continue

            # Check ignored domains
            if any(re.search(pat, url, re.IGNORECASE) for pat in ignored_patterns):
                continue

            normalized = clean_url(url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                aggregated_sources.append(r)
                if len(aggregated_sources) >= max_total_sources:
                    return aggregated_sources

    return aggregated_sources
