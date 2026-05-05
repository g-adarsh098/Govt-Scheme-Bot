"""
rag_pipeline.py — LangChain RAG chain for Government Scheme queries
Uses: Gemini 1.5 Flash LLM + Google Embeddings + ChromaDB retriever
"""

import os
import logging
from pathlib import Path
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.documents import Document

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Paths & Config ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
CHROMA_DIR = Path(os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "chroma_db")))
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
COLLECTION_NAME = "govt_schemes"

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful, accurate, and empathetic AI assistant specializing in Indian Government schemes and welfare programs.

CRITICAL INSTRUCTION: You MUST respond ENTIRELY in {response_language}. Do NOT mix languages. Every single word of your response must be in {response_language} only.

Your role:
- Help citizens understand government schemes, eligibility criteria, benefits, and application processes
- Provide accurate information based on the retrieved context
- Be empathetic and use simple language accessible to common citizens
- Always mention the official portal or helpline when available
- If you don't know something, say so honestly — do NOT hallucinate

Guidelines:
- Structure your responses clearly (Eligibility, Benefits, How to Apply, Documents Needed)
- For application steps, use numbered lists
- Cite which scheme or document your information comes from
- Respond ONLY in {response_language} — this is mandatory

Context from documents:
{context}

Chat History:
{chat_history}
"""

HUMAN_PROMPT = "Question: {question}"

# ── Prompt Template ────────────────────────────────────────────────────────────
def build_prompt(lang_name: str = "English") -> ChatPromptTemplate:
    prompt_text = SYSTEM_PROMPT.replace("{response_language}", lang_name)
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(prompt_text),
        HumanMessagePromptTemplate.from_template(HUMAN_PROMPT),
    ])


# ── Retriever ──────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma | None:
    """Load ChromaDB vector store (cached singleton)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        logger.error("GOOGLE_API_KEY not set. Please configure .env")
        return None
    if not CHROMA_DIR.exists():
        logger.warning(f"ChromaDB not found at {CHROMA_DIR}. Run ingest.py first.")
        return None
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=api_key,
        )
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR),
        )
        logger.info("✅ ChromaDB loaded successfully")
        return vectorstore
    except Exception as e:
        logger.error(f"Failed to load ChromaDB: {e}")
        return None


def get_retriever(k: int = 5):
    """Get a top-k similarity retriever."""
    vs = get_vectorstore()
    if vs is None:
        return None
    return vs.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


# ── LLM ────────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI | None:
    """Instantiate the Gemini LLM (cached singleton)."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        return None
    try:
        return ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=api_key,
            temperature=0.3,
            max_output_tokens=2048,
        )
    except Exception as e:
        logger.error(f"Failed to load LLM: {e}")
        return None


# ── Chain Builder ──────────────────────────────────────────────────────────────
def build_chain(session_memory=None, target_lang_name: str = "English"):
    """Build a ConversationalRetrievalChain with optional persistent memory."""
    llm = get_llm()
    retriever = get_retriever()

    if llm is None or retriever is None:
        return None

    memory = session_memory or ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
        k=5,  # Keep last 5 exchanges
    )

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": build_prompt(target_lang_name)},
        return_source_documents=True,
        verbose=False,
    )
    return chain


# ── Public Query Function ──────────────────────────────────────────────────────
def query_rag(
    question: str,
    chat_history: list[tuple[str, str]] | None = None,
    lang: str = "en",
    target_lang_name: str = "English",
) -> dict[str, Any]:
    """
    Run a RAG query and return answer + sources.

    Args:
        question: User question (in English; translation happens in main.py)
        chat_history: List of (human, ai) message tuples
        lang: Target language code for metadata

    Returns:
        dict with keys: answer, sources, model, language
    """
    chain = build_chain(target_lang_name=target_lang_name)
    if chain is None:
        return {
            "answer": (
                "⚠️ The bot is not configured yet. Please set your GOOGLE_API_KEY "
                "in the .env file and run `python backend/ingest.py` to load documents."
            ),
            "sources": [],
            "model": LLM_MODEL,
            "language": lang,
            "error": "configuration_error",
        }

    history = chat_history or []
    formatted_history = [(h, a) for h, a in history]

    try:
        result = chain.invoke({
            "question": question,
            "chat_history": formatted_history,
        })

        # Extract unique source files
        source_docs: list[Document] = result.get("source_documents", [])
        sources = list({
            doc.metadata.get("source_file", doc.metadata.get("source", "Unknown"))
            for doc in source_docs
        })

        answer = result.get("answer", "").strip()
        if not answer:
            answer = "I could not find specific information about that. Please try rephrasing your question."

        return {
            "answer": answer,
            "sources": sources,
            "model": LLM_MODEL,
            "language": lang,
            "error": None,
        }

    except Exception as e:
        logger.error(f"RAG query error: {e}")
        # Fallback: try a direct LLM answer without retrieval
        try:
            llm = get_llm()
            if llm:
                fallback = llm.invoke(
                    f"You are a helpful assistant for Indian government schemes. Answer this question briefly: {question}"
                )
                return {
                    "answer": fallback.content,
                    "sources": [],
                    "model": LLM_MODEL,
                    "language": lang,
                    "error": "retrieval_failed_used_fallback",
                }
        except Exception as fe:
            logger.error(f"Fallback LLM also failed: {fe}")
        return {
            "answer": f"⚠️ I encountered an error: {str(e)[:200]}. Please check the backend logs.",
            "sources": [],
            "model": LLM_MODEL,
            "language": lang,
            "error": str(e),
        }


# ── Similarity Search (for debug/dev) ─────────────────────────────────────────
def semantic_search(query: str, k: int = 5) -> list[dict]:
    """Return top-k similar document chunks for a query."""
    vs = get_vectorstore()
    if vs is None:
        return []
    results = vs.similarity_search_with_score(query, k=k)
    return [
        {
            "content": doc.page_content[:500],
            "metadata": doc.metadata,
            "score": round(float(score), 4),
        }
        for doc, score in results
    ]
