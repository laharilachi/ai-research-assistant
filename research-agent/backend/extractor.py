"""Web content extraction and cleaning using Trafilatura.
Concurrently fetches web pages, strips boilerplate/navigation, and retains clean article text.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import requests
import trafilatura
from backend.config import MAX_CONTENT_CHARS

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_source_content(source: Dict[str, str], timeout: int = 10) -> Optional[Dict[str, str]]:
    """Fetches and extracts clean body text from a single source dictionary.
    
    Args:
        source: Dictionary with 'title', 'url', and 'snippet'.
        timeout: Network request timeout in seconds.
        
    Returns:
        Dict containing title, url, snippet, and extracted clean text, or fallback snippet.
    """
    url = source.get("url", "")
    extracted_text = ""

    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        if response.status_code == 200 and response.text:
            extracted_text = trafilatura.extract(
                response.text,
                include_links=False,
                include_images=False,
                include_tables=True,
                favor_precision=True,
            ) or ""
    except Exception as e:
        logger.debug(f"Trafilatura download/extract failed for {url}: {e}")

    # Fallback to search snippet if extraction was empty or failed
    final_text = (extracted_text.strip() or source.get("snippet", "")).strip()
    if not final_text:
        return None

    # Limit text length to prevent context explosion while maintaining high density
    if len(final_text) > MAX_CONTENT_CHARS:
        final_text = final_text[:MAX_CONTENT_CHARS] + "\n...[truncated]"

    return {
        "title": source.get("title", "Untitled Source"),
        "url": url,
        "snippet": source.get("snippet", ""),
        "text": final_text,
    }


def fetch_all_sources(sources: List[Dict[str, str]], max_workers: int = 6) -> List[Dict[str, str]]:
    """Concurrently extracts content for a list of search hits.
    
    Args:
        sources: List of search result dictionaries.
        max_workers: Thread pool concurrency.
        
    Returns:
        List of enriched source dictionaries with extracted clean text.
    """
    results: List[Dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(extract_source_content, src): src for src in sources
        }
        for future in as_completed(future_to_source):
            try:
                data = future.result()
                if data and data.get("text"):
                    results.append(data)
            except Exception as e:
                logger.warning(f"Error processing source extraction: {e}")

    # Retain stable ordering by URL matching original search preference
    url_order = {src["url"]: idx for idx, src in enumerate(sources)}
    results.sort(key=lambda s: url_order.get(s["url"], 999))
    return results
