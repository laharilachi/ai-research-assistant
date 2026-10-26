"""Convenience script to launch the Streamlit application."""
import sys
import subprocess

if __name__ == "__main__":
    print("Launching Streamlit AI Research Assistant...")
    cmd = [sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py"]
    subprocess.run(cmd)
