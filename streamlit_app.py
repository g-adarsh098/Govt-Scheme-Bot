"""
streamlit_app.py — Root entry point for Streamlit Cloud deployment.

Streamlit Cloud auto-detects this file at the repo root and uses it as the
app entry point, preventing it from accidentally picking up backend/main.py.
"""
# ── SQLite3 version fix for ChromaDB on Streamlit Cloud ──────────────────────
# ChromaDB requires sqlite3 >= 3.35.0. Streamlit Cloud's default Linux image
# ships with an older version. pysqlite3-binary provides a newer one.
# This MUST be the very first import in the entry point.
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# ─────────────────────────────────────────────────────────────────────────────

import runpy
from pathlib import Path

# Execute the actual frontend app in place (preserves __file__, __name__, etc.)
runpy.run_path(str(Path(__file__).parent / "frontend" / "app.py"), run_name="__main__")
