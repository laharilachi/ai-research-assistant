"""Unit and integration test suite for the research assistant RAG pipeline."""
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.agent import run_research


def mock_call_llm(prompt, system_prompt=None, **kwargs):
    if "Generate exactly" in prompt:
        return '["quantum algorithms overview", "quantum computing applications"]'
    elif "Analyze the following webpage" in prompt:
        return "This source explains quantum algorithms and superposition principles."
    elif "Conduct a thorough research investigation" in prompt:
        return (
            "# Quantum Computing Advances\n\n"
            "## Executive Summary\n"
            "Quantum computing represents an exponential leap over classical computing [1].\n\n"
            "## Technical Architecture & Core Concepts\n"
            "Qubits utilize quantum superposition and entanglement to execute operations [1][2].\n\n"
            "## Conclusion\n"
            "Hardware scalability remains the primary focus of active research [2]."
        )
    return "Mock response"


def test_research_pipeline():
    with patch("backend.agent.get_llm", return_value=(None, "groq", "llama-3.3-70b-versatile")):
        with patch("backend.agent.call_llm", side_effect=mock_call_llm):
            events = []

            def on_progress(step, msg, pct, data):
                events.append((step, pct, msg))

            res = run_research(
                "Quantum computing algorithms",
                num_queries=2,
                progress_callback=on_progress,
            )

            assert res.topic == "Quantum computing algorithms"
            assert res.provider_used == "groq"
            assert len(res.queries) == 2
            assert len(res.sources) > 0
            assert len(res.bibliography) > 0
            assert "[1]" in res.report
            assert "## Bibliography" in res.report
            print("All pipeline assertions passed successfully!")


if __name__ == "__main__":
    test_research_pipeline()
