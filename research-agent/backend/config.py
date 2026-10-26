"""Configuration module for AI Research Assistant.
Handles environment variables, API key validation, and model defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current directory, backend directory, and parent directory
env_paths = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
    Path(__file__).resolve().parent.parent / ".env",
]

for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p)
        break
else:
    load_dotenv()  # Fallback to default search

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "6"))
MAX_CONTENT_CHARS = int(os.getenv("MAX_CONTENT_CHARS", "6000"))
DEFAULT_NUM_QUERIES = 5


def get_active_provider(override_provider: str | None = None) -> tuple[str, str]:
    """Determines the active LLM provider and model name.
    
    Preference rules:
    1. Explicit override if provided and key exists.
    2. Explicit LLM_PROVIDER from env if its corresponding key exists.
    3. Groq (prefer Groq if key exists as per project requirement).
    4. OpenAI if key exists.
    5. Error with helpful setup instructions.
    
    Returns:
        tuple[str, str]: (provider_name, model_name)
    """
    selected = (override_provider or LLM_PROVIDER).lower()

    if selected == "groq" and GROQ_API_KEY:
        return "groq", GROQ_MODEL
    if selected == "openai" and OPENAI_API_KEY:
        return "openai", OPENAI_MODEL

    # Auto-detection preference: Groq first, then OpenAI
    if GROQ_API_KEY:
        return "groq", GROQ_MODEL
    if OPENAI_API_KEY:
        return "openai", OPENAI_MODEL

    raise ValueError(
        "No valid LLM API key detected. Please set GROQ_API_KEY or OPENAI_API_KEY in your .env file."
    )
