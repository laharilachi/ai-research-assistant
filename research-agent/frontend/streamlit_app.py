"""Streamlit Frontend for AI Research Assistant.
Provides a clean, web-like UI with real-time research progress tracking,
formatted markdown preview, and one-click Markdown file download.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path so backend imports work reliably
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from backend.agent import run_research
from backend.config import GROQ_API_KEY, OPENAI_API_KEY, get_active_provider

# Page Configuration
st.set_page_config(
    page_title="AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Web Styling to make it look like a clean modern website
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .main {
        background-color: #f8fafc;
    }

    .block-container {
        max-width: 950px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .hero-title {
        font-size: 2.25rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }

    .hero-sub {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }

    .provider-badge {
        display: inline-block;
        background-color: #ccfbf1;
        color: #0f766e;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    .stTextInput > div > div > input {
        font-size: 1rem;
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }

    .report-card {
        background: #ffffff;
        padding: 2.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        font-family: 'Source Serif 4', Georgia, serif;
        font-size: 1.1rem;
        line-height: 1.8;
        color: #1e293b;
    }

    .report-card h1, .report-card h2, .report-card h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .source-box {
        background: #f1f5f9;
        border-left: 4px solid #0f766e;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown('<div class="hero-title">🔬 AI Research Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Autonomous RAG Agent: Multi-query Search &bull; Trafilatura Extraction &bull; Grounded Citations</div>',
    unsafe_allow_html=True,
)

# Check active provider
try:
    provider_name, model_name = get_active_provider()
    st.markdown(
        f'<span class="provider-badge">ACTIVE ENGINE: {provider_name.upper()} ({model_name})</span>',
        unsafe_allow_html=True,
    )
except Exception as e:
    st.error(
        "⚠️ No API key detected. Please configure `GROQ_API_KEY` (preferred) or `OPENAI_API_KEY` in your `.env` file."
    )

# Input Box and Button
col_input, col_btn = st.columns([4, 1])

with col_input:
    topic_query = st.text_input(
        "Research Topic",
        placeholder="e.g. Current breakthroughs and commercial viability of solid-state batteries...",
        label_visibility="collapsed",
    )

with col_btn:
    start_clicked = st.button("Start Research", type="primary", use_container_width=True)

# Sample Topics chips
st.markdown("<small style='color: #64748b;'>**Quick suggestions:**</small>", unsafe_allow_html=True)
sample_cols = st.columns(4)
suggestions = [
    "Solid-state battery commercialization",
    "Quantum error correction milestones",
    "Autonomous AI agent architectures",
    "Nuclear fusion net energy gain",
]

for i, sug in enumerate(suggestions):
    if sample_cols[i].button(sug, key=f"sug_{i}", use_container_width=True):
        topic_query = sug
        start_clicked = True

# Main Execution Trigger
if start_clicked and topic_query.strip():
    topic = topic_query.strip()
    
    # Progress UI
    progress_bar = st.progress(0)
    status_container = st.status("🚀 Initializing research pipeline...", expanded=True)
    
    pipeline_state = {
        "queries": [],
        "sources": [],
    }

    def on_progress(step: str, message: str, percent: int, data: any = None):
        progress_bar.progress(percent)
        status_container.update(label=f"🔄 {message}")
        if step == "planning" and data and "queries" in data:
            pipeline_state["queries"] = data["queries"]
        if step == "searching" and data and "queries" in data:
            status_container.write(f"Generated {len(data['queries'])} queries: " + ", ".join(f"`{q}`" for q in data["queries"]))

    try:
        with status_container:
            result = run_research(
                topic=topic,
                num_queries=5,
                progress_callback=on_progress,
            )
            status_container.update(
                label="✅ Research report synthesized successfully!",
                state="complete",
                expanded=False,
            )
        
        progress_bar.progress(100)

        # Store in session state for persistence
        st.session_state["last_result"] = result

    except Exception as err:
        status_container.update(label=f"❌ Error during research: {str(err)}", state="error")
        st.error(f"Execution Error: {str(err)}")

# Display Cached or New Result
if "last_result" in st.session_state:
    res = st.session_state["last_result"]

    st.markdown("---")
    
    # Actions: Download & Metadata
    col_meta, col_dl = st.columns([3, 1])
    with col_meta:
        st.caption(f"**Topic:** {res.topic} | **Engine:** {res.provider_used.upper()} ({res.model_used}) | **Sources Analyzed:** {len(res.sources)}")
    
    with col_dl:
        clean_name = res.topic.lower().replace(" ", "-")[:40]
        st.download_button(
            label="📥 Download Markdown",
            data=res.report,
            file_name=f"research-{clean_name}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Tabs: Report, Sources, Generated Queries
    tab_report, tab_sources, tab_queries = st.tabs(["📄 Research Report", "📚 Retrieved Sources", "🔍 Search Queries"])

    with tab_report:
        st.markdown(res.report)

    with tab_sources:
        st.subheader("Numbered Sources & Extracted Evidence")
        for src in res.sources:
            with st.expander(f"[{src.id}] {src.title}", expanded=False):
                st.markdown(f"**URL:** [{src.url}]({src.url})")
                if src.summary:
                    st.markdown(f"**Factual Summary:**\n{src.summary}")
                elif src.snippet:
                    st.markdown(f"**Snippet:**\n{src.snippet}")

    with tab_queries:
        st.subheader("LLM-Generated Search Queries")
        for i, q in enumerate(res.queries, start=1):
            st.markdown(f"- **Query {i}:** `{q}`")
