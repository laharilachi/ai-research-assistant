"""FastAPI backend application for AI Research Assistant.
Provides REST and SSE endpoints for research pipeline execution and static UI hosting.
"""
import asyncio
import json
import logging
import queue
import threading
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.agent import run_research
from backend.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    get_active_provider,
)
from backend.models import HealthResponse, ResearchRequest, ResearchResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("research_assistant")

app = FastAPI(
    title="AI Research Assistant API",
    description="Backend API powered by FastAPI, LangChain, DuckDuckGo, and Trafilatura.",
    version="1.0.0",
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for static website
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "static"


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Checks configuration status and active model provider."""
    has_groq = bool(GROQ_API_KEY)
    has_openai = bool(OPENAI_API_KEY)

    active_provider = None
    active_model = None
    status = "healthy"

    try:
        active_provider, active_model = get_active_provider()
    except Exception as e:
        status = f"unconfigured: {str(e)}"

    return HealthResponse(
        status=status,
        has_groq=has_groq,
        has_openai=has_openai,
        active_provider=active_provider,
        active_model=active_model,
    )


@app.post("/api/research", response_model=ResearchResponse)
def conduct_research(request: ResearchRequest):
    """Executes the full RAG research pipeline synchronously and returns final report."""
    topic = request.topic.strip()
    if len(topic) < 3:
        raise HTTPException(status_code=400, detail="Research topic must be at least 3 characters.")

    try:
        logger.info(f"Received research request: '{topic}'")
        result = run_research(
            topic=topic,
            num_queries=request.num_queries or 5,
            provider_override=request.provider,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Research execution failed")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.get("/api/research/stream")
async def stream_research(
    topic: str = Query(..., min_length=3, description="Topic to research"),
    provider: str | None = Query(None, description="Optional LLM provider ('groq' or 'openai')"),
    num_queries: int = Query(5, ge=4, le=6, description="Number of queries to generate"),
):
    """Server-Sent Events (SSE) streaming endpoint providing live step progress updates."""
    clean_topic = topic.strip()
    if len(clean_topic) < 3:
        raise HTTPException(status_code=400, detail="Topic must be at least 3 characters.")

    event_queue: queue.Queue = queue.Queue()

    def progress_callback(step: str, message: str, progress: int, data: any = None):
        event_queue.put({
            "type": "progress",
            "step": step,
            "message": message,
            "progress": progress,
            "data": data,
        })

    def worker():
        try:
            result = run_research(
                topic=clean_topic,
                num_queries=num_queries,
                provider_override=provider,
                progress_callback=progress_callback,
            )
            event_queue.put({
                "type": "complete",
                "result": result.model_dump(),
            })
        except Exception as exc:
            logger.exception("Error in streaming research worker")
            event_queue.put({
                "type": "error",
                "message": str(exc),
            })
        finally:
            event_queue.put(None)  # Sentinel

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    async def event_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        while True:
            # Non-blocking poll from thread queue
            event = await loop.run_in_executor(None, event_queue.get)
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Mount static website directory if it exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def serve_index():
        """Serves the main website user interface."""
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "AI Research Assistant API is running. Static UI not yet created."}
