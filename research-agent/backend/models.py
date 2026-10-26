"""Data models for AI Research Assistant."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Incoming request to execute a research query."""
    topic: str = Field(..., min_length=3, description="Topic or question to research")
    provider: Optional[str] = Field(None, description="Optional LLM provider ('groq' or 'openai')")
    num_queries: Optional[int] = Field(5, ge=4, le=6, description="Number of search queries to generate (4-6)")


class SourceItem(BaseModel):
    """Metadata and content for a retrieved source."""
    id: int
    title: str
    url: str
    snippet: str
    content: Optional[str] = None
    summary: Optional[str] = None


class BibliographyItem(BaseModel):
    """Numbered bibliography entry."""
    id: int
    title: str
    url: str


class ProgressUpdate(BaseModel):
    """Real-time progress update event."""
    step: str
    message: str
    progress: int
    data: Optional[Any] = None


class ResearchResponse(BaseModel):
    """Complete research synthesis response."""
    topic: str
    queries: list[str]
    sources: list[SourceItem]
    report: str
    bibliography: list[BibliographyItem]
    provider_used: str
    model_used: str


class HealthResponse(BaseModel):
    """Health check status response."""
    status: str
    has_groq: bool
    has_openai: bool
    active_provider: Optional[str] = None
    active_model: Optional[str] = None
