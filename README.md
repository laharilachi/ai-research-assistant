# 🔬 AI Research Assistant

An autonomous research agent and grounded RAG (Retrieval-Augmented Generation) application with a FastAPI backend, modern web UI, and Streamlit frontend. It generates deep, cited, and strictly evidence-grounded research reports on any topic.

---

## 🌟 Key Features

1. **Intelligent Query Generation**: Uses LLMs (`ChatGroq` with `llama-3.3-70b-versatile` or `ChatOpenAI`) to expand the research topic into 4–6 targeted, orthogonal web queries covering definitions, architectures, state-of-the-art advances, risks, and benchmarks.
2. **Web Search via DuckDuckGo**: High-coverage search across all queries with URL deduplication and domain filtering.
3. **Clean Content Extraction with Trafilatura**: Automatically fetches web pages and strips boilerplate, navigation bars, and ads to extract clean article text. Gracefully falls back to search snippets if a page is blocked or paywalled.
4. **LLM Source Summarization**: Concurrently synthesizes factual summaries (key claims, figures, findings) strictly from the extracted text.
5. **Strict Grounded RAG Synthesis**: Enforces strict grounding rules — the report is constructed **only** from retrieved sources without hallucination or external speculation.
6. **In-Text Citations & Bibliography**: Every claim includes inline numerical citations `[1]`, `[2]`, `[3]`, accompanied by a formatted `Bibliography` section mapping each source number to its title and URL.
7. **Two Frontend Options**:
   - **Modern Web UI**: A responsive website interface with real-time SSE progress streaming, animated step indicators, markdown formatting, copy button, and `.md` file download.
   - **Streamlit UI**: Fast, interactive Python dashboard with live status containers, expandable source cards, and instant download buttons.

---

## 📁 Project Structure

```text
research-agent/
│
├── backend/
│   ├── __init__.py
│   ├── config.py           # Environment variables & provider auto-detection
│   ├── models.py           # Pydantic schemas for requests, responses & events
│   ├── llm_client.py       # LangChain ChatGroq & ChatOpenAI factory
│   ├── search.py           # DuckDuckGo multi-query search & deduplication
│   ├── extractor.py        # Trafilatura concurrent content extraction
│   ├── agent.py            # Complete RAG research orchestrator & citations
│   └── main.py             # FastAPI app with REST, SSE streams & static UI
│
├── frontend/
│   ├── static/             # Built-in modern website frontend
│   │   ├── index.html      # Responsive HTML5 layout & stepper UI
│   │   ├── styles.css      # Modern typography & styles
│   │   └── app.js          # EventSource (SSE) streaming & marked.js rendering
│   └── streamlit_app.py    # Alternative Streamlit application
│
├── .env.example            # Sample configuration for Groq & OpenAI API keys
├── requirements.txt        # Python package dependencies
├── run_backend.py          # FastAPI launch script
├── run_frontend.py         # Streamlit launch script
└── README.md               # Documentation & usage guide
```

---

## ⚙️ Installation & Setup

### 1. Clone or Open the Workspace
```bash
cd research-agent
```

### 2. Create and Activate a Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔑 Configure API Keys

Copy the sample environment file:
```bash
# Windows PowerShell
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and provide your API key:

### Option A: Groq (Recommended & Preferred)
Get a free API key at [console.groq.com](https://console.groq.com/keys):
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
```

### Option B: OpenAI
Get an API key at [platform.openai.com](https://platform.openai.com/api-keys):
```ini
OPENAI_API_KEY=sk-proj-your_openai_api_key_here
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
```

---

## 🚀 Running the Application

### Option 1: Start the Web Application (FastAPI + Modern Web UI)

Run the backend server:
```bash
python run_backend.py
```
*Or using uvicorn directly:*
```bash
uvicorn backend.main:app --reload --port 8000
```

Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

This serves the modern web interface with real-time SSE progress updates, query tag pills, styled citations, and one-click Markdown downloads.

---

### Option 2: Run with Streamlit

Run the Streamlit application:
```bash
python run_frontend.py
```
*Or via streamlit CLI:*
```bash
streamlit run frontend/streamlit_app.py
```

Open your browser to:
👉 **[http://localhost:8501](http://localhost:8501)**

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive Web UI |
| `GET` | `/api/health` | Health status and active LLM provider check |
| `POST` | `/api/research` | Synchronous research endpoint returning `ResearchResponse` JSON |
| `GET` | `/api/research/stream?topic=...` | Server-Sent Events (SSE) streaming progress and report payload |

### Example Request (`POST /api/research`):
```json
{
  "topic": "State of solid-state batteries in 2026",
  "num_queries": 5,
  "provider": "groq"
}
```

---

## 🧠 How the RAG Pipeline Works

```text
User Research Topic
        │
        ▼
[1] LLM Query Planner (LangChain + Groq/OpenAI)
        ├─► Generates 4-6 orthogonal, high-yield search queries
        │
        ▼
[2] DuckDuckGo Search Engine
        ├─► Multi-query search execution
        ├─► URL deduplication & domain filtering
        │
        ▼
[3] Trafilatura Web Scraper
        ├─► Parallel web content extraction
        ├─► Boilerplate, header, and ad stripping
        ├─► Fallback to search snippets if unreachable
        │
        ▼
[4] Source Summarization (LLM)
        ├─► Extracts key metrics, mechanisms, and factual claims
        │
        ▼
[5] Strict Grounded RAG Synthesis (LLM)
        ├─► Strictly constrained to retrieved sources
        ├─► Formulates Title, Executive Summary, Headings
        ├─► Injects in-text citations [1], [2], [3]
        │
        ▼
[6] Bibliography & Output
        ├─► Assembles verified bibliography
        └─► Exports Markdown report (.md)
```
