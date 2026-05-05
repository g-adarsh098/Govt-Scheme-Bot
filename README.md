# 🇮🇳 Govt Scheme Bot — Multilingual RAG Chatbot

A production-ready RAG (Retrieval-Augmented Generation) chatbot for **Indian government welfare schemes**, powered by **Google Gemini**, **LangChain**, and **ChromaDB**. Supports **10 Indian languages** with automatic detection and translation.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **RAG Pipeline** | LangChain + Gemini 1.5 Flash + ChromaDB vector store |
| **Languages** | English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi |
| **Document Types** | PDF, TXT, MD, FAQ files + auto-generated glossary |
| **Conversation Memory** | Sliding window of last 5 exchanges per session |
| **Frontend** | Streamlit with dark glassmorphism UI |
| **Backend** | FastAPI with session management + background ingestion |
| **Schemes Covered** | PM-KISAN, PMJAY, PMAY, MGNREGS, PMJJBY, PMSBY, NSAP + 3000+ via documents |

---

## 📁 Project Structure

```
govt-scheme-bot/
├── backend/
│   ├── main.py          # FastAPI REST API (chat, search, health, session)
│   ├── rag_pipeline.py  # LangChain ConversationalRetrievalChain
│   ├── ingest.py        # Document loader, chunker & ChromaDB embedder
│   └── translate.py     # Language detection & translation helpers
├── frontend/
│   └── app.py           # Streamlit chat UI
├── data/
│   ├── raw/             # Drop your PDFs & .txt/.faq files here
│   ├── chroma_db/       # Auto-generated vector store (git-ignored)
│   └── glossary.json    # 8 schemes × 10 languages multilingual glossary
├── requirements.txt
└── .env                 # Your API key goes here
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd "Govt Scheme Bot"
pip install -r requirements.txt
```

### 2. Configure API Key

Edit `.env`:
```env
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

Get a free API key at: https://aistudio.google.com/app/apikey

### 3. Add Documents (Optional)

Drop any PDFs or text files into `data/raw/`. The bot ships with seed FAQ data covering 10 major schemes.

```
data/raw/
├── pm_kisan_guidelines.pdf
├── ayushman_bharat.pdf
└── any_govt_circular.txt
```

### 4. Ingest Documents

```bash
python backend/ingest.py
```

This will:
- Load all PDFs, text files, and the glossary
- Split into overlapping chunks (1000 chars, 200 overlap)
- Embed using `models/embedding-001`
- Persist to `data/chroma_db/`

### 5. Start the Backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 6. Start the Frontend

```bash
streamlit run frontend/app.py
```

Open: http://localhost:8501

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API, vector store, and key status |
| POST | `/chat` | Main chat endpoint with session & translation |
| POST | `/search` | Direct semantic search for debugging |
| GET | `/languages` | List all supported languages |
| GET | `/greeting?lang=hi` | Get greeting in any language |
| POST | `/ingest` | Trigger re-ingestion in background |
| DELETE | `/session/{id}` | Clear a conversation session |

### Chat Request Example

```json
POST /chat
{
  "question": "PM-KISAN के लिए कौन पात्र है?",
  "session_id": "optional-uuid",
  "language": "hi",
  "translate_response": true
}
```

---

## 🏗️ Architecture

```
User Query (any language)
       │
       ▼
   [Streamlit UI]
       │  HTTP
       ▼
   [FastAPI /chat]
       │
       ├── Language Detection (googletrans)
       ├── Translation → English (deep-translator)
       │
       ▼
   [LangChain RAG Chain]
       │
       ├── ChromaDB Retriever (top-5 similar chunks)
       ├── Gemini 1.5 Flash (LLM)
       └── Conversation Memory (last 5 turns)
       │
       ▼
   English Answer
       │
       ├── Translate → User Language
       └── Return to UI with sources
```

---

## 🌍 Supported Languages

| Language | Code | Script |
|---|---|---|
| English | en | Latin |
| हिंदी Hindi | hi | Devanagari |
| தமிழ் Tamil | ta | Tamil |
| తెలుగు Telugu | te | Telugu |
| বাংলা Bengali | bn | Bengali |
| मराठी Marathi | mr | Devanagari |
| ગુજરાતી Gujarati | gu | Gujarati |
| ಕನ್ನಡ Kannada | kn | Kannada |
| മലയാളം Malayalam | ml | Malayalam |
| ਪੰਜਾਬੀ Punjabi | pa | Gurmukhi |

---

## 📄 Adding Your Own Documents

1. Drop PDFs/TXT files into `data/raw/`
2. For FAQ files, use `.faq` extension with `Q: ... A: ...` format
3. Re-run: `python backend/ingest.py`

The bot supports:
- **PDF** — Government circulars, scheme guidelines
- **TXT/MD** — Plain text, markdown documents
- **FAQ** — Q&A pairs (`.faq` extension)
- **JSON** — The glossary auto-loads

---

## ⚙️ Configuration

All settings in `.env`:

```env
GOOGLE_API_KEY=your_key
LLM_MODEL=gemini-1.5-flash          # or gemini-1.5-pro for better quality
EMBEDDING_MODEL=models/embedding-001
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
DEFAULT_LANGUAGE=en
```

---

## 📦 Tech Stack

- **LLM**: Google Gemini 1.5 Flash (via `langchain-google-genai`)
- **Embeddings**: Google `embedding-001`
- **Vector DB**: ChromaDB (local persistence)
- **Framework**: LangChain `ConversationalRetrievalChain`
- **API**: FastAPI + Uvicorn
- **UI**: Streamlit
- **Translation**: deep-translator + googletrans
- **Doc Loading**: LangChain community loaders (PyPDF, TextLoader)

---

## 🤝 Data Sources

- [myScheme Portal](https://www.myscheme.gov.in)
- [PM-KISAN](https://pmkisan.gov.in)
- [Ayushman Bharat PMJAY](https://pmjay.gov.in)
- [PMAY](https://pmaymis.gov.in)
- [MGNREGS](https://nrega.nic.in)

> **Note**: This bot is for informational purposes. Always verify with official government portals.
