"""
main.py — FastAPI backend for the Govt Scheme Bot
Endpoints: /chat, /search, /languages, /health, /ingest
"""

import os
import sys
import uuid
import logging
from typing import Any
from pathlib import Path

# Add the backend directory to sys.path to fix import errors when running from root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from rag_pipeline import query_rag, semantic_search, get_vectorstore
from translate import (
    detect_language_safe,
    translate_to_english,
    translate_from_english,
    get_language_greeting,
    SUPPORTED_LANGS,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Session store (in-memory; replace with Redis in production) ────────────────
_sessions: dict[str, dict[str, Any]] = {}

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Govt Scheme Bot API",
    description="Multilingual RAG chatbot for Indian government welfare schemes",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    session_id: str | None = Field(None, description="Session ID for conversation continuity")
    language: str | None = Field(None, description="ISO 639-1 language code; auto-detected if omitted")
    translate_response: bool = Field(True, description="Translate response back to user's language")


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    detected_language: str
    language_name: str
    sources: list[str]
    model: str
    error: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    k: int = Field(5, ge=1, le=20)


class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float


class HealthResponse(BaseModel):
    status: str
    vectorstore_ready: bool
    api_key_set: bool
    version: str


# ── Helper ─────────────────────────────────────────────────────────────────────
def get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    """Retrieve or create a session by ID."""
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {"history": [], "message_count": 0}
    return new_id, _sessions[new_id]


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Govt Scheme Bot API is running 🇮🇳",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """Check API health and dependencies."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    vs = get_vectorstore()
    return HealthResponse(
        status="healthy",
        vectorstore_ready=vs is not None,
        api_key_set=bool(api_key and api_key != "your_google_api_key_here"),
        version="1.0.0",
    )


@app.get("/languages", tags=["Utilities"])
async def get_supported_languages():
    """Return all supported languages."""
    return {
        "languages": SUPPORTED_LANGS,
        "default": "en",
        "count": len(SUPPORTED_LANGS),
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest):
    """
    Main chat endpoint.
    - Auto-detects or uses provided language
    - Translates question → English → RAG → response → user language
    - Maintains conversation history per session
    """
    # ── Session management ────────────────────────────────────────────────
    session_id, session = get_or_create_session(req.session_id)

    # ── Language detection ────────────────────────────────────────────────
    user_lang = req.language or detect_language_safe(req.question)
    lang_names = {v: k for k, v in SUPPORTED_LANGS.items()}
    lang_display = lang_names.get(user_lang, "English")

    logger.info(f"[{session_id[:8]}] Lang={user_lang} | Q={req.question[:80]}")

    # ── Translate question to English for retrieval ───────────────────────
    question_en = req.question
    if user_lang != "en":
        question_en = translate_to_english(req.question, source_lang=user_lang)
        logger.info(f"[{session_id[:8]}] Translated: {question_en[:80]}")

    # ── RAG query (pass target_lang so LLM responds in that language) ────
    rag_result = query_rag(
        question=question_en,
        chat_history=session["history"],
        lang=user_lang,
        target_lang_name=lang_display,
    )

    answer = rag_result["answer"]

    # ── Translation safety net (only if LLM ignored the language instruction)
    # We skip translation for English and trust the LLM for other languages.
    # Translation via deep_translator produces mixed/garbled output for
    # structured content, so the LLM-level instruction is the primary fix.
    if req.translate_response and user_lang != "en" and rag_result.get("error"):
        # Only translate as a fallback when RAG itself errored (used direct LLM)
        answer = translate_from_english(answer, target_lang=user_lang)

    # ── Update session history ────────────────────────────────────────────
    session["history"].append((req.question, answer))
    session["message_count"] += 1
    if len(session["history"]) > 10:
        session["history"] = session["history"][-10:]

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        detected_language=user_lang,
        language_name=lang_display,
        sources=rag_result.get("sources", []),
        model=rag_result.get("model", "gemini-2.5-flash"),
        error=rag_result.get("error"),
    )


@app.post("/search", response_model=list[SearchResult], tags=["Search"])
async def semantic_search_endpoint(req: SearchRequest):
    """
    Direct semantic search against the vector store.
    Useful for debugging retrieval quality.
    """
    results = semantic_search(req.query, k=req.k)
    if not results:
        raise HTTPException(
            status_code=503,
            detail="Vector store not available. Run ingest.py first.",
        )
    return [SearchResult(**r) for r in results]


@app.post("/ingest", tags=["Admin"])
async def trigger_ingest(background_tasks: BackgroundTasks):
    """Trigger document ingestion in the background."""
    def run_ingest():
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from ingest import ingest
            ingest()
        except Exception as e:
            logger.error(f"Ingestion error: {e}")

    background_tasks.add_task(run_ingest)
    return {"message": "Ingestion started in background. Check server logs."}


@app.get("/session/{session_id}", tags=["Session"])
async def get_session_info(session_id: str):
    """Get session metadata (message count, history length)."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[session_id]
    return {
        "session_id": session_id,
        "message_count": session["message_count"],
        "history_length": len(session["history"]),
    }


@app.delete("/session/{session_id}", tags=["Session"])
async def clear_session(session_id: str):
    """Clear a conversation session."""
    if session_id in _sessions:
        del _sessions[session_id]
    return {"message": f"Session {session_id} cleared"}


@app.get("/greeting", tags=["Utilities"])
async def get_greeting(lang: str = "en"):
    """Get a welcome greeting in the specified language."""
    return {"greeting": get_language_greeting(lang), "language": lang}


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
