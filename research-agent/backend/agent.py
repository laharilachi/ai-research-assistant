"""Full RAG Research Pipeline Agent.
Orchestrates:
1. Query generation (4-6 queries via LLM)
2. DuckDuckGo search
3. Trafilatura clean content extraction
4. Source summarization via LLM
5. Grounded RAG report synthesis with citations [1], [2], [3]
6. Bibliography assembly
"""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from backend.config import DEFAULT_NUM_QUERIES, MAX_SEARCH_RESULTS
from backend.extractor import fetch_all_sources
from backend.llm_client import call_llm, get_llm
from backend.models import BibliographyItem, ResearchResponse, SourceItem
from backend.search import search_multiple_queries

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str, str, int, Optional[Any]], None]]


def plan_queries(
    topic: str,
    num_queries: int = DEFAULT_NUM_QUERIES,
    provider_override: Optional[str] = None,
) -> List[str]:
    """Generates 4-6 orthogonal, high-yield search queries using the LLM.
    
    Args:
        topic: The research topic input by the user.
        num_queries: Number of queries to generate (4-6).
        provider_override: Optional LLM provider.
        
    Returns:
        List of generated query strings.
    """
    system_prompt = (
        "You are an expert research strategist. Your task is to break down a topic "
        "into distinct, targeted web search queries to gather comprehensive, balanced information."
    )
    prompt = f"""Generate exactly {num_queries} diverse search queries to thoroughly research the following topic:
Topic: "{topic}"

Ensure the queries cover:
1. Fundamental definitions and technical overview
2. Modern developments and state-of-the-art advances
3. Key challenges, risks, limitations, or criticisms
4. Concrete data, performance statistics, or real-world use cases

Output format: Return ONLY a valid JSON list of strings, with no markdown formatting or extra text.
Example: ["query 1", "query 2", "query 3", "query 4", "query 5"]
"""

    response = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        provider_override=provider_override,
        temperature=0.3,
        max_tokens=600,
    )

    # Clean markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", response).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            return [str(q).strip() for q in data][:6]
    except Exception as e:
        logger.warning(f"JSON parsing failed for queries: {e}. Falling back to regex extraction.")

    # Fallback line-by-line parsing
    lines = [
        re.sub(r"^\d+[\.\-\)]\s*", "", line).strip(' "[],\'')
        for line in response.splitlines()
        if line.strip() and not line.strip().startswith("[") and not line.strip().endswith("]")
    ]
    valid_lines = [line for line in lines if len(line) > 5]
    if valid_lines:
        return valid_lines[:num_queries]

    # Absolute fallback
    return [
        topic,
        f"{topic} overview and architecture",
        f"{topic} latest research 2025 2026",
        f"{topic} challenges and limitations",
    ]


def summarize_source(
    source: Dict[str, str],
    provider_override: Optional[str] = None,
) -> Dict[str, str]:
    """Summarizes a single extracted source strictly using its factual content."""
    prompt = f"""Analyze the following webpage extract and produce a factual 100-150 word summary.
Document Title: {source.get('title', 'Unknown')}
URL: {source.get('url', '')}

Extracted Text:
{source.get('text', '')}

Guidelines:
- Extract specific metrics, mechanisms, findings, organizations, and claims.
- Strictly include ONLY facts directly stated in the text.
- Do not extrapolate or add outside knowledge.

Summary:"""

    try:
        summary = call_llm(
            prompt=prompt,
            system_prompt="You are a strict, objective fact extractor. Extract only what is written.",
            provider_override=provider_override,
            temperature=0.1,
            max_tokens=400,
        )
        source["summary"] = summary.strip()
    except Exception as e:
        logger.warning(f"Summarization failed for {source.get('url')}: {e}")
        source["summary"] = source.get("snippet", "No summary available.")

    return source


def summarize_all_sources(
    sources: List[Dict[str, str]],
    provider_override: Optional[str] = None,
    max_workers: int = 5,
) -> List[Dict[str, str]]:
    """Summarizes all retrieved sources concurrently."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        summarized = list(
            executor.map(
                lambda s: summarize_source(s, provider_override=provider_override),
                sources,
            )
        )
    return summarized


def synthesize_rag_report(
    topic: str,
    sources: List[Dict[str, str]],
    provider_override: Optional[str] = None,
) -> str:
    """Synthesizes the final research report with in-text citations [1], [2], [3]
    strictly grounded in the retrieved sources (RAG constraint).
    """
    # Build indexed context with citations
    context_blocks = []
    for idx, s in enumerate(sources, start=1):
        block = (
            f"SOURCE [{idx}]:\n"
            f"Title: {s.get('title', 'Unknown')}\n"
            f"URL: {s.get('url', '')}\n"
            f"Summary: {s.get('summary', '')}\n"
            f"Excerpt: {s.get('text', '')[:1800]}\n"
        )
        context_blocks.append(block)

    joined_sources = "\n----------------------------------------\n".join(context_blocks)

    system_prompt = (
        "You are an elite research analyst and scientific writer. "
        "You synthesize rigorous, clear, and comprehensive research reports. "
        "STRICT RAG RULE: You must ONLY use the information provided in the numbered sources. "
        "Do NOT introduce external assumptions or unverified claims. Every factual statement "
        "MUST include an in-text citation pointing to the source number, e.g. [1] or [2][3]."
    )

    user_prompt = f"""Conduct a thorough research investigation on:
Topic: "{topic}"

Carefully analyze the retrieved sources below and write a comprehensive, professional Markdown research report.

STRUCTURE REQUIREMENTS:
# [Report Title]

## Executive Summary
A high-level synthesis of the topic and core findings.

## Technical Architecture & Core Concepts
Detailed explanation of principles, mechanisms, and key components.

## Recent Advances & Developments
Current breakthroughs, benchmark figures, and trends based on the sources.

## Critical Challenges & Trade-offs
Limitations, obstacles, risks, or contrasting viewpoints.

## Future Outlook & Conclusion
Summary of the landscape and concluding perspective.

CITATION RULES:
- Attribute all facts, numbers, dates, and claims with inline bracketed numbers matching the sources: e.g., "...as demonstrated in recent trials [1]." or "...showing a 35% efficiency boost [2][4]."
- Do NOT fabricate citations or cite indices greater than {len(sources)}.
- Do NOT write the bibliography section yourself; it will be formatted programmatically from your citations.

RETRIEVED SOURCES:
{joined_sources}
"""

    report = call_llm(
        prompt=user_prompt,
        system_prompt=system_prompt,
        provider_override=provider_override,
        temperature=0.2,
        max_tokens=3500,
    )
    return report.strip()


def run_research(
    topic: str,
    num_queries: int = DEFAULT_NUM_QUERIES,
    provider_override: Optional[str] = None,
    progress_callback: ProgressCallback = None,
) -> ResearchResponse:
    """Executes the full end-to-end RAG research pipeline.
    
    Args:
        topic: User's research topic.
        num_queries: Number of queries to plan (4-6).
        provider_override: Optional override for 'groq' or 'openai'.
        progress_callback: Optional callable(step, message, percentage, data) for live telemetry.
        
    Returns:
        ResearchResponse model.
    """
    clean_topic = topic.strip()
    if len(clean_topic) < 3:
        raise ValueError("Research topic must be at least 3 characters long.")

    # 1. Resolve LLM provider & model
    _, provider_name, model_name = get_llm(provider_override=provider_override)

    # 2. Plan Queries
    if progress_callback:
        progress_callback("planning", "Generating 4-6 targeted search queries using LLM...", 10, None)
    queries = plan_queries(clean_topic, num_queries=num_queries, provider_override=provider_override)
    logger.info(f"Planned queries for '{clean_topic}': {queries}")

    if progress_callback:
        progress_callback("searching", f"Searching DuckDuckGo across {len(queries)} queries...", 30, {"queries": queries})

    # 3. DuckDuckGo Web Search
    search_hits = search_multiple_queries(queries, max_total_sources=MAX_SEARCH_RESULTS)
    if not search_hits:
        # Fallback to direct topic search
        search_hits = search_multiple_queries([clean_topic], max_total_sources=4)

    if not search_hits:
        raise RuntimeError(f"No web sources found for topic: '{clean_topic}'. Please try refining the topic.")

    # 4. Extract content via Trafilatura
    if progress_callback:
        progress_callback("extracting", f"Extracting clean text from {len(search_hits)} sources using Trafilatura...", 50, None)
    extracted_sources = fetch_all_sources(search_hits)
    if not extracted_sources:
        extracted_sources = search_hits  # Snippet fallback

    # 5. Summarize Sources
    if progress_callback:
        progress_callback("summarizing", f"Summarizing {len(extracted_sources)} sources with LLM...", 70, None)
    summarized_sources = summarize_all_sources(extracted_sources, provider_override=provider_override)

    # 6. Synthesize Grounded RAG Report
    if progress_callback:
        progress_callback("synthesizing", "Synthesizing structured RAG research report with in-text citations...", 85, None)
    raw_report = synthesize_rag_report(clean_topic, summarized_sources, provider_override=provider_override)

    # 7. Assemble Structured Sources & Bibliography
    source_items: List[SourceItem] = []
    for idx, s in enumerate(summarized_sources, start=1):
        source_items.append(
            SourceItem(
                id=idx,
                title=s.get("title", f"Source {idx}"),
                url=s.get("url", ""),
                snippet=s.get("snippet", ""),
                content=s.get("text", "")[:1000] if s.get("text") else None,
                summary=s.get("summary", ""),
            )
        )

    # Extract all citations present in the report
    cited_numbers = set()
    for match in re.finditer(r"\[(\d+)\]", raw_report):
        try:
            num = int(match.group(1))
            if 1 <= num <= len(source_items):
                cited_numbers.add(num)
        except ValueError:
            pass

    # If no citations were parsed or model omitted them, include all retrieved sources in bibliography
    if not cited_numbers:
        cited_numbers = set(range(1, len(source_items) + 1))

    sorted_citations = sorted(cited_numbers)
    bibliography: List[BibliographyItem] = [
        BibliographyItem(
            id=n,
            title=source_items[n - 1].title,
            url=source_items[n - 1].url,
        )
        for n in sorted_citations
    ]

    # Append formal Bibliography section to the report markdown if not already present
    if "## Bibliography" not in raw_report:
        bib_lines = ["\n\n## Bibliography\n"]
        for b in bibliography:
            bib_lines.append(f"[{b.id}] [{b.title}]({b.url})\n")
        final_report = raw_report + "".join(bib_lines)
    else:
        final_report = raw_report

    if progress_callback:
        progress_callback("completed", "Research report generated successfully!", 100, {"report_ready": True})

    return ResearchResponse(
        topic=clean_topic,
        queries=queries,
        sources=source_items,
        report=final_report,
        bibliography=bibliography,
        provider_used=provider_name,
        model_used=model_name,
    )
