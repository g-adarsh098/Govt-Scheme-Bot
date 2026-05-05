"""
translate.py — Language detection & translation helpers
Supports 10 Indian languages via deep-translator + googletrans fallback.
"""

import json
import os
from pathlib import Path
from functools import lru_cache

from deep_translator import GoogleTranslator
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
GLOSSARY_PATH = Path(__file__).parent.parent / "data" / "glossary.json"

SUPPORTED_LANGS: dict[str, str] = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "தமிழ் (Tamil)": "ta",
    "తెలుగు (Telugu)": "te",
    "বাংলা (Bengali)": "bn",
    "मराठी (Marathi)": "mr",
    "ગુજરાતી (Gujarati)": "gu",
    "ಕನ್ನಡ (Kannada)": "kn",
    "മലയാളം (Malayalam)": "ml",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
}

LANG_CODE_TO_NAME = {v: k for k, v in SUPPORTED_LANGS.items()}


# ── Glossary ───────────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_glossary() -> dict:
    """Load the multilingual glossary JSON (cached)."""
    if GLOSSARY_PATH.exists():
        with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_scheme_in_lang(scheme_key: str, lang: str) -> str | None:
    """Return the scheme name in the target language, if available."""
    glossary = load_glossary()
    schemes = glossary.get("schemes", {})
    if scheme_key in schemes and lang in schemes[scheme_key]:
        return schemes[scheme_key][lang]
    return None


# ── Detection ──────────────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    """
    Detect the language of `text`.
    Returns an ISO 639-1 code (e.g. 'hi', 'en', 'ta').
    Falls back to 'en' on any error.
    """
    try:
        from langdetect import detect
        return detect(text[:500])
    except Exception:
        return "en"


def detect_language_safe(text: str) -> str:
    """Best-effort language detection; always returns a valid supported code."""
    code = detect_language(text)
    supported_codes = set(SUPPORTED_LANGS.values())
    return code if code in supported_codes else "en"


# ── Translation ────────────────────────────────────────────────────────────────
def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Translate `text` from `source_lang` to `target_lang`.
    Returns original text on failure.
    """
    if target_lang == "en" and source_lang in ("en", "auto"):
        return text
    if not text.strip():
        return text
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        # deep-translator has a 5000 char limit per request
        if len(text) <= 4500:
            return translator.translate(text)
        # Chunk large texts
        chunks = _chunk_text(text, 4000)
        translated_chunks = [translator.translate(chunk) for chunk in chunks]
        return " ".join(translated_chunks)
    except Exception as exc:
        print(f"[translate] Translation error ({source_lang}→{target_lang}): {exc}")
        return text


def translate_to_english(text: str, source_lang: str = "auto") -> str:
    """Translate any language to English for RAG retrieval."""
    return translate_text(text, target_lang="en", source_lang=source_lang)


def translate_from_english(text: str, target_lang: str) -> str:
    """Translate English LLM output to user's language."""
    if target_lang == "en":
        return text
    return translate_text(text, target_lang=target_lang, source_lang="en")


# ── Helpers ────────────────────────────────────────────────────────────────────
def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most `max_chars` chars at sentence boundaries."""
    chunks, current = [], ""
    for sentence in text.split(". "):
        if len(current) + len(sentence) + 2 <= max_chars:
            current += sentence + ". "
        else:
            if current:
                chunks.append(current.strip())
            current = sentence + ". "
    if current:
        chunks.append(current.strip())
    return chunks or [text]


def get_language_greeting(lang_code: str) -> str:
    """Return a greeting in the user's language."""
    greetings = {
        "en": "Hello! How can I help you with government schemes today?",
        "hi": "नमस्ते! आज मैं सरकारी योजनाओं के बारे में आपकी कैसे मदद कर सकता हूँ?",
        "ta": "வணக்கம்! இன்று அரசு திட்டங்களில் உங்களுக்கு எவ்வாறு உதவலாம்?",
        "te": "నమస్కారం! నేడు ప్రభుత్వ పథకాల గురించి మీకు ఎలా సహాయం చేయగలను?",
        "bn": "নমস্কার! আজ সরকারি প্রকল্প সম্পর্কে আপনাকে কীভাবে সাহায্য করতে পারি?",
        "mr": "नमस्कार! आज मी सरकारी योजनांबद्दल तुम्हाला कशी मदत करू शकतो?",
        "gu": "નમસ્તે! આજે સરકારી યોજનાઓ વિશે હું તમારી કેવી રીતે મદદ કરી શકું?",
        "kn": "ನಮಸ್ಕಾರ! ಇಂದು ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
        "ml": "നമസ്കാരം! ഇന്ന് സർക്കാർ പദ്ധതികളെക്കുറിച്ച് നിങ്ങളെ എങ്ങനെ സഹായിക്കാൻ കഴിയും?",
        "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਅੱਜ ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਬਾਰੇ ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    }
    return greetings.get(lang_code, greetings["en"])
