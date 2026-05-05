"""
streamlit_app.py — Root entry point for Streamlit Cloud deployment.

Streamlit Cloud auto-detects this file at the repo root and uses it as the
app entry point, preventing it from accidentally picking up backend/main.py.
"""
import runpy
from pathlib import Path

# Execute the actual frontend app in place (preserves __file__, __name__, etc.)
runpy.run_path(str(Path(__file__).parent / "frontend" / "app.py"), run_name="__main__")
