"""Convenience script to launch the FastAPI backend server and web UI."""
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting AI Research Assistant on http://localhost:{port}")
    print(f"Open http://localhost:{port} in your browser to use the Web UI.")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
