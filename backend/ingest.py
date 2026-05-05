"""
ingest.py — Document loader, chunker, and vector store builder
Run: python backend/ingest.py
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
    JSONLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = Path(os.getenv("RAW_DATA_PATH", str(BASE_DIR / "data" / "raw")))
CHROMA_DIR = Path(os.getenv("CHROMA_DB_PATH", str(BASE_DIR / "data" / "chroma_db")))
GLOSSARY_PATH = BASE_DIR / "data" / "glossary.json"

# ── Config ─────────────────────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
COLLECTION_NAME = "govt_schemes"


# ── Loaders ────────────────────────────────────────────────────────────────────
def load_pdfs(directory: Path) -> list[Document]:
    """Load all PDF documents from a directory recursively."""
    docs = []
    pdf_files = list(directory.rglob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {directory}")
        return docs
    for pdf_path in pdf_files:
        try:
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()
            for page in pages:
                page.metadata["source_file"] = pdf_path.name
                page.metadata["file_type"] = "pdf"
            docs.extend(pages)
            logger.info(f"  Loaded PDF: {pdf_path.name} ({len(pages)} pages)")
        except Exception as e:
            logger.error(f"  Failed to load {pdf_path.name}: {e}")
    return docs


def load_text_files(directory: Path) -> list[Document]:
    """Load .txt and .md files."""
    docs = []
    for pattern in ["*.txt", "*.md"]:
        for fpath in directory.rglob(pattern):
            try:
                loader = TextLoader(str(fpath), encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["source_file"] = fpath.name
                    doc.metadata["file_type"] = "text"
                docs.extend(loaded)
                logger.info(f"  Loaded text: {fpath.name}")
            except Exception as e:
                logger.error(f"  Failed to load {fpath.name}: {e}")
    return docs


def load_glossary_as_docs(glossary_path: Path) -> list[Document]:
    """Convert glossary schemes into searchable documents."""
    docs = []
    if not glossary_path.exists():
        return docs
    with open(glossary_path, "r", encoding="utf-8") as f:
        glossary = json.load(f)

    schemes = glossary.get("schemes", {})
    for scheme_key, info in schemes.items():
        content = (
            f"Scheme: {info.get('full_name', scheme_key)}\n"
            f"Short name: {scheme_key}\n"
            f"Category: {info.get('category', 'N/A')}\n"
            f"Benefit: {info.get('benefit_amount', 'N/A')}\n"
            f"Target beneficiaries: {info.get('target', 'N/A')}\n"
        )
        if "hi" in info:
            content += f"Hindi name: {info['hi']}\n"
        docs.append(Document(
            page_content=content,
            metadata={
                "source_file": "glossary.json",
                "file_type": "glossary",
                "scheme_key": scheme_key,
                "category": info.get("category", "general"),
            }
        ))
    logger.info(f"  Loaded {len(docs)} schemes from glossary")
    return docs


def load_faq_docs(directory: Path) -> list[Document]:
    """Load FAQ text files (expected format: Q: ... A: ...) as Documents."""
    docs = []
    for fpath in directory.rglob("*.faq"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append(Document(
                page_content=content,
                metadata={"source_file": fpath.name, "file_type": "faq"}
            ))
            logger.info(f"  Loaded FAQ: {fpath.name}")
        except Exception as e:
            logger.error(f"  Failed FAQ {fpath.name}: {e}")
    return docs


# ── Chunker ────────────────────────────────────────────────────────────────────
def split_documents(docs: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "।", ".", " ", ""],  # includes Devanagari separator
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    logger.info(f"Split {len(docs)} docs → {len(chunks)} chunks")
    return chunks


# ── Embedder & Store ───────────────────────────────────────────────────────────
def build_vector_store(chunks: list[Document]) -> Chroma:
    """Embed chunks and persist to ChromaDB."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_google_api_key_here":
        raise ValueError("Set GOOGLE_API_KEY in your .env file before ingesting.")

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
    )

    logger.info(f"Building ChromaDB at {CHROMA_DIR} ...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    # Batch embed to avoid rate limits
    batch_size = 50
    all_batches = [chunks[i:i+batch_size] for i in range(0, len(chunks), batch_size)]

    vectorstore = None
    for i, batch in enumerate(all_batches):
        logger.info(f"  Embedding batch {i+1}/{len(all_batches)} ({len(batch)} chunks)...")
        if vectorstore is None:
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=str(CHROMA_DIR),
            )
        else:
            vectorstore.add_documents(batch)
        if i < len(all_batches) - 1:
            time.sleep(1)  # Respect API rate limits

    logger.info("✅ Vector store built and persisted.")
    return vectorstore


# ── Seed FAQ Content ───────────────────────────────────────────────────────────
SEED_FAQS = """
Q: What is PM-KISAN?
A: PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) is a central sector scheme that provides income support of ₹6,000 per year in three equal instalments of ₹2,000 to all landholding farmer families across the country. The amount is directly transferred to the bank accounts of the beneficiaries.

Q: Who is eligible for PM-KISAN?
A: All landholding farmer families with cultivable land are eligible. However, the following are excluded: institutional land holders; farmer families holding constitutional posts; serving or retired officers of state/central government services; income tax payers; doctors, engineers, lawyers, chartered accountants and architects registered with professional bodies.

Q: What is Ayushman Bharat PMJAY?
A: Pradhan Mantri Jan Arogya Yojana (PMJAY) is the world's largest health insurance scheme, providing health cover of ₹5 lakh per family per year for secondary and tertiary care hospitalization. It covers over 10.74 crore poor and vulnerable families (approximately 50 crore beneficiaries).

Q: How do I apply for Ayushman Bharat?
A: You can check your eligibility and apply through: 1) The official PMJAY website (pmjay.gov.in), 2) Common Service Centres (CSC), 3) Hospitals empanelled under PMJAY, 4) Ayushman Bharat mobile app. A family identified in SECC 2011 data is automatically covered.

Q: What is PMAY (Pradhan Mantri Awas Yojana)?
A: PMAY is a housing scheme aimed at providing affordable housing to urban and rural poor. Under PMAY-Urban, interest subsidy is provided on home loans. Under PMAY-Gramin, financial assistance is given for construction of pucca houses. Beneficiaries get ₹1.20 lakh to ₹1.30 lakh in plain areas and ₹1.30 lakh in hilly/difficult areas.

Q: What is MGNREGA?
A: The Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA) guarantees 100 days of wage employment in a financial year to rural households whose adult members volunteer to do unskilled manual work. The current wage rate varies by state, averaging ₹220-350 per day.

Q: What documents are needed for ration card?
A: To apply for a ration card you typically need: Aadhaar card of all family members, proof of residence (electricity bill, rent agreement), passport-size photographs, income certificate, and bank account details. Requirements vary by state.

Q: What is the PM Ujjwala Yojana?
A: PMUY provides free LPG connections to women from Below Poverty Line (BPL) households. Each beneficiary gets a free deposit-free LPG connection. The scheme aims to safeguard the health of women and children by moving away from traditional cooking fuels.

Q: What is the National Pension System (NPS)?
A: NPS is a voluntary, long-term retirement savings scheme designed to enable systematic savings. Subscribers contribute regularly during their working life. At retirement, subscribers can withdraw a portion as lump sum and use the remaining corpus to buy an annuity. The government contributes 14% of salary for central government employees.

Q: How do I check scheme eligibility?
A: You can check eligibility through: 1) myScheme portal (myscheme.gov.in) which has 3000+ schemes with eligibility filters, 2) Jan Samarth portal for credit-linked schemes, 3) Official ministry websites, 4) Common Service Centres (CSC) in your area. You can filter by state, age, gender, income, and category.
""".strip()


def create_seed_faq(raw_dir: Path) -> None:
    """Write seed FAQ data if the raw directory is empty."""
    faq_file = raw_dir / "seed_faqs.txt"
    if not faq_file.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        faq_file.write_text(SEED_FAQS, encoding="utf-8")
        logger.info(f"Created seed FAQ file: {faq_file}")


# ── Main ───────────────────────────────────────────────────────────────────────
def ingest() -> None:
    logger.info("=" * 60)
    logger.info("Govt Scheme Bot — Document Ingestion Pipeline")
    logger.info("=" * 60)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Create seed content if no data exists yet
    create_seed_faq(RAW_DIR)

    # Load all document types
    all_docs: list[Document] = []
    logger.info(f"\n📂 Loading documents from {RAW_DIR}...")
    all_docs.extend(load_pdfs(RAW_DIR))
    all_docs.extend(load_text_files(RAW_DIR))
    all_docs.extend(load_faq_docs(RAW_DIR))
    all_docs.extend(load_glossary_as_docs(GLOSSARY_PATH))

    if not all_docs:
        logger.error("No documents found to ingest. Add PDFs or .txt files to data/raw/")
        sys.exit(1)

    logger.info(f"\n📄 Total documents loaded: {len(all_docs)}")

    # Chunk
    logger.info("\n✂️  Splitting into chunks...")
    chunks = split_documents(all_docs)

    # Embed and store
    logger.info("\n🔮 Embedding and storing in ChromaDB...")
    build_vector_store(chunks)

    logger.info("\n🎉 Ingestion complete!")
    logger.info(f"   Total chunks stored: {len(chunks)}")
    logger.info(f"   Vector DB location: {CHROMA_DIR}")


if __name__ == "__main__":
    ingest()
