"""
app.py — Streamlit Chat UI for Govt Scheme Bot (Modern UI)
Run: streamlit run frontend/app.py
"""
import os, uuid, json, requests
from pathlib import Path
from datetime import datetime
import streamlit as st

BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
GLOSSARY_PATH = Path(__file__).parent.parent / "data" / "glossary.json"

st.set_page_config(page_title="Scheme Bot 🇮🇳", page_icon="🇮🇳", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans Devanagari', sans-serif; }

/* ── Animated Background ── */
.stApp {
    background: linear-gradient(-45deg, #0a0a1a, #0f0f2e, #1a0a2e, #0a1a2e);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Floating particles ── */
.particles {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    pointer-events: none; z-index: 0; overflow: hidden;
}
.particle {
    position: absolute; width: 4px; height: 4px;
    background: rgba(139,92,246,0.4); border-radius: 50%;
    animation: float linear infinite;
}
@keyframes float {
    0%   { transform: translateY(100vh) rotate(0deg); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { transform: translateY(-100px) rotate(720deg); opacity: 0; }
}

/* ── Block container ── */
.block-container { padding-top: 0.5rem !important; position: relative; z-index: 1; }

/* ── Main Header ── */
.hero-header {
    background: linear-gradient(135deg, rgba(79,70,229,0.9) 0%, rgba(124,58,237,0.9) 50%, rgba(219,39,119,0.9) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.15);
    padding: 2rem 2.5rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(79,70,229,0.4), 0 0 60px rgba(124,58,237,0.2);
    animation: heroGlow 3s ease-in-out infinite alternate;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute; top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%);
    animation: shimmer 4s linear infinite;
}
@keyframes heroGlow {
    from { box-shadow: 0 8px 32px rgba(79,70,229,0.4), 0 0 40px rgba(124,58,237,0.2); }
    to   { box-shadow: 0 8px 48px rgba(79,70,229,0.6), 0 0 80px rgba(219,39,119,0.3); }
}
@keyframes shimmer {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
.hero-header h1 {
    color: white; font-size: 2.2rem; font-weight: 800; margin: 0;
    text-shadow: 0 2px 20px rgba(0,0,0,0.4);
    letter-spacing: -0.5px;
    animation: textPop 0.6s ease-out;
}
.hero-header p {
    color: rgba(255,255,255,0.85); font-size: 0.95rem; margin: 0.5rem 0 0;
    animation: textPop 0.8s ease-out;
}
@keyframes textPop {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hero-badges {
    display: flex; justify-content: center; gap: 0.6rem;
    margin-top: 1rem; flex-wrap: wrap;
}
.hero-badge {
    background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25);
    color: white; font-size: 0.75rem; padding: 4px 12px;
    border-radius: 20px; backdrop-filter: blur(10px);
    animation: badgeFade 1s ease-out;
}
@keyframes badgeFade {
    from { opacity: 0; transform: scale(0.8); }
    to   { opacity: 1; transform: scale(1); }
}

/* ── Welcome screen ── */
.welcome-screen {
    text-align: center; padding: 4rem 1rem 2rem;
    animation: fadeInUp 0.8s ease-out;
}
.welcome-icon {
    font-size: 5rem; margin-bottom: 1.5rem;
    animation: pulse 2s ease-in-out infinite;
    display: block;
}
@keyframes pulse {
    0%, 100% { transform: scale(1); filter: drop-shadow(0 0 10px rgba(139,92,246,0.5)); }
    50%       { transform: scale(1.05); filter: drop-shadow(0 0 20px rgba(219,39,119,0.6)); }
}
.welcome-title {
    color: #a5b4fc; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.8rem;
    background: linear-gradient(135deg, #a5b4fc, #f0abfc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.welcome-desc {
    color: rgba(255,255,255,0.6); max-width: 520px; margin: 0 auto;
    line-height: 1.8; font-size: 1rem;
}
.welcome-hint {
    margin-top: 2rem; color: #7c3aed; font-size: 0.9rem;
    animation: bounce 2s ease-in-out infinite;
    display: inline-block;
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-5px); }
}
.feature-chips {
    display: flex; justify-content: center; gap: 1rem;
    margin-top: 1.5rem; flex-wrap: wrap;
}
.feature-chip {
    background: rgba(79,70,229,0.15); border: 1px solid rgba(79,70,229,0.4);
    color: #a5b4fc; padding: 8px 16px; border-radius: 30px;
    font-size: 0.85rem; transition: all 0.3s;
}

/* ── Chat messages ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Source chips ── */
.source-chip {
    display: inline-block;
    background: rgba(79,70,229,0.2); border: 1px solid rgba(79,70,229,0.4);
    color: #a5b4fc; font-size: 0.7rem; padding: 2px 10px;
    border-radius: 20px; margin: 2px; transition: all 0.2s;
}
.source-chip:hover { background: rgba(79,70,229,0.4); }

/* ── Sidebar — smooth slide panel ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a0a1e 0%, #0f0a2e 100%) !important;
    border-right: 1px solid rgba(139,92,246,0.25) !important;
    box-shadow: 6px 0 48px rgba(79,70,229,0.35) !important;
    transition: transform 0.45s cubic-bezier(0.22,1,0.36,1),
                box-shadow 0.45s cubic-bezier(0.22,1,0.36,1),
                width 0.45s cubic-bezier(0.22,1,0.36,1) !important;
}

/* Toggle button — positioned top-left, not middle */
[data-testid="stSidebarCollapseButton"] {
    position: fixed !important;
    top: 1rem !important;
    left: 0 !important;
    transform: none !important;
    z-index: 9999 !important;
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    border-radius: 0 10px 10px 0 !important;
    width: 32px !important;
    height: 48px !important;
    box-shadow: 4px 0 16px rgba(79,70,229,0.55) !important;
    cursor: pointer !important;
    transition: width 0.25s cubic-bezier(0.22,1,0.36,1),
                box-shadow 0.25s ease,
                background 0.25s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    animation: tabPulse 3s ease-in-out infinite !important;
}
@keyframes tabPulse {
    0%, 100% { box-shadow: 4px 0 16px rgba(79,70,229,0.55); }
    50%       { box-shadow: 4px 0 28px rgba(124,58,237,0.85); }
}
[data-testid="stSidebarCollapseButton"]:hover {
    width: 40px !important;
    box-shadow: 6px 0 32px rgba(124,58,237,0.8) !important;
    background: linear-gradient(135deg, #6366f1, #a78bfa) !important;
    animation: none !important;
}
[data-testid="stSidebarCollapseButton"] svg {
    width: 15px !important; height: 15px !important;
    stroke: white !important; fill: none !important;
    transition: transform 0.3s ease !important;
}

/* Sidebar inner padding */
[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }

/* Sidebar logo / header */
.sidebar-logo {
    text-align: center; padding: 1rem 0 0.8rem;
    border-bottom: 1px solid rgba(139,92,246,0.2);
    margin-bottom: 0.8rem;
    background: linear-gradient(180deg, rgba(79,70,229,0.08), transparent);
}
.sidebar-logo h2 {
    color: white; font-size: 1.2rem; font-weight: 800; margin: 0;
    background: linear-gradient(135deg, #a5b4fc, #f0abfc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.3px;
}
.sidebar-logo p { color: rgba(255,255,255,0.35); font-size: 0.68rem; margin: 4px 0 0; letter-spacing: 0.02em; }

/* Status card */
.status-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 0.75rem 1rem;
    margin-bottom: 0.75rem; position: relative; overflow: hidden;
    transition: border-color 0.3s;
}
.status-card:hover { border-color: rgba(139,92,246,0.3); }
.status-card::before {
    content: ''; position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(to bottom, #4f46e5, #db2777);
    border-radius: 2px;
}
.status-online  { color: #34d399; font-size: 0.85rem; font-weight: 600; }
.status-offline { color: #f87171; font-size: 0.85rem; font-weight: 600; }
.status-meta { font-size: 0.74rem; color: #64748b; margin-top: 4px; }

.section-label {
    color: #6366f1; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    padding: 0.6rem 0 0.4rem;
    border-bottom: 1px solid rgba(99,102,241,0.2);
    margin: 0.5rem 0 0.5rem;
}

/* ── Buttons (ALL) ── */
.stButton > button {
    background: linear-gradient(135deg, rgba(79,70,229,0.8), rgba(124,58,237,0.8)) !important;
    color: white !important; border: 1px solid rgba(139,92,246,0.4) !important;
    border-radius: 10px !important; font-weight: 500 !important;
    font-size: 0.82rem !important; transition: all 0.25s ease !important;
    box-shadow: 0 2px 10px rgba(79,70,229,0.25) !important;
    backdrop-filter: blur(10px) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(79,70,229,0.5) !important;
    border-color: rgba(165,180,252,0.6) !important;
}
.stButton > button:active {
    transform: translateY(0px) !important;
    box-shadow: 0 2px 10px rgba(79,70,229,0.3) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(139,92,246,0.3) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 4px 24px rgba(79,70,229,0.2) !important;
    transition: all 0.3s !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(139,92,246,0.7) !important;
    box-shadow: 0 4px 32px rgba(79,70,229,0.4) !important;
}
[data-testid="stChatInput"] textarea {
    color: #e2e8f0 !important; font-family: 'Inter', sans-serif !important;
    background: transparent !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    animation: fadeInUp 0.4s ease-out;
    background: transparent !important;
}
[data-testid="stChatMessageAvatarUser"]   { background: linear-gradient(135deg, #4f46e5, #7c3aed) !important; }
[data-testid="stChatMessageAvatarAssistant"] { background: linear-gradient(135deg, #0f172a, #1e1b4b) !important; border: 1px solid rgba(139,92,246,0.4) !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(139,92,246,0.3) !important;
    border-radius: 10px !important; color: #e2e8f0 !important;
}

/* ── Metric ── */
[data-testid="stMetric"] { background: rgba(79,70,229,0.1) !important; border-radius: 10px !important; padding: 0.5rem !important; }
[data-testid="stMetricValue"] { color: #a5b4fc !important; }

/* ── Divider ── */
hr { border-color: rgba(139,92,246,0.2) !important; margin: 0.5rem 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 10px; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #7c3aed !important; }
</style>

<!-- Floating particles -->
<div class="particles">
  <div class="particle" style="left:10%;animation-duration:12s;animation-delay:0s;width:3px;height:3px"></div>
  <div class="particle" style="left:25%;animation-duration:18s;animation-delay:3s;background:rgba(219,39,119,0.4)"></div>
  <div class="particle" style="left:40%;animation-duration:14s;animation-delay:1s;width:6px;height:6px;opacity:0.3"></div>
  <div class="particle" style="left:60%;animation-duration:20s;animation-delay:5s;background:rgba(99,102,241,0.5)"></div>
  <div class="particle" style="left:75%;animation-duration:16s;animation-delay:2s;width:3px;height:3px"></div>
  <div class="particle" style="left:90%;animation-duration:13s;animation-delay:7s;background:rgba(167,139,250,0.4)"></div>
  <div class="particle" style="left:50%;animation-duration:22s;animation-delay:4s;width:5px;height:5px;opacity:0.2"></div>
</div>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_languages():
    try:
        r = requests.get(f"{BACKEND_URL}/languages", timeout=5)
        if r.ok: return r.json().get("languages", {})
    except: pass
    return {"English":"en","हिंदी (Hindi)":"hi","தமிழ் (Tamil)":"ta",
            "తెలుగు (Telugu)":"te","বাংলা (Bengali)":"bn","मराठी (Marathi)":"mr",
            "ગુજરાતી (Gujarati)":"gu","ಕನ್ನಡ (Kannada)":"kn","മലയാളം (Malayalam)":"ml","ਪੰਜਾਬੀ (Punjabi)":"pa"}

@st.cache_data(ttl=60)
def check_health():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if r.ok: return r.json()
    except: pass
    return {"status":"offline","vectorstore_ready":False,"api_key_set":False}

@st.cache_data(ttl=3600)
def load_glossary():
    if GLOSSARY_PATH.exists():
        with open(GLOSSARY_PATH,"r",encoding="utf-8") as f: return json.load(f)
    return {}

def send_chat(question, session_id, lang_code):
    try:
        r = requests.post(f"{BACKEND_URL}/chat",
            json={"question":question,"session_id":session_id,"language":lang_code},timeout=60)
        if r.ok: return r.json()
        return {"answer":f"❌ Error {r.status_code}","sources":[],"error":str(r.status_code)}
    except requests.exceptions.ConnectionError:
        return {"answer":"⚠️ **Backend offline.** Run:\n```\nuvicorn backend.main:app --reload --port 8000\n```","sources":[],"error":"connection_error"}
    except Exception as e:
        return {"answer":f"❌ {e}","sources":[],"error":str(e)}


# ── Session State ────────────────────────────────────────────────────────────────
for k,v in [("session_id",str(uuid.uuid4())),("messages",[]),("selected_lang","en"),("lang_name","English"),("quick_question","")]:
    if k not in st.session_state: st.session_state[k] = v


# ── Sidebar ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h2>🇮🇳 Scheme Bot</h2>
        <p>Multilingual Government AI Assistant</p>
    </div>""", unsafe_allow_html=True)

    # Status
    h = check_health()
    ok = h.get("status") == "healthy"
    st.markdown(f"""
    <div class="status-card">
        <div class="{'status-online' if ok else 'status-offline'}">
            {'🟢 Online' if ok else '🔴 Offline'} &nbsp;·&nbsp; {h.get('status','unknown').title()}
        </div>
        <div class="status-meta">
            Vector DB {'✅' if h.get('vectorstore_ready') else '❌'} &nbsp;|&nbsp; API Key {'✅' if h.get('api_key_set') else '❌'}
        </div>
    </div>""", unsafe_allow_html=True)

    # Language
    st.markdown('<div class="section-label">🌐 Language</div>', unsafe_allow_html=True)
    langs = fetch_languages()
    lang_choice = st.selectbox("Language", list(langs.keys()), index=0, label_visibility="collapsed", key="lang_selector")
    st.session_state.selected_lang = langs[lang_choice]
    st.session_state.lang_name     = lang_choice

    # Popular Schemes
    glossary = load_glossary()
    schemes  = glossary.get("schemes", {})
    if schemes:
        st.markdown('<div class="section-label">🎯 Popular Schemes</div>', unsafe_allow_html=True)
        for key, info in list(schemes.items())[:6]:
            if st.button(f"📋 {key}", key=f"s_{key}", use_container_width=True, help=info.get("full_name", key)):
                st.session_state.quick_question = f"Tell me about {info.get('full_name', key)} scheme"
                st.rerun()

    # Sample Questions
    st.markdown('<div class="section-label">💡 Ask Me</div>', unsafe_allow_html=True)
    for q in ["Who is eligible for PM-KISAN?","How to apply for Ayushman Bharat?",
              "Documents needed for PMAY?","MGNREGA work days limit?","PMJJBY benefit amount?"]:
        if st.button(q, key=f"q_{q[:16]}", use_container_width=True):
            st.session_state.quick_question = q
            st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []; st.session_state.session_id = str(uuid.uuid4()); st.rerun()
    with c2:
        st.metric("Msgs", len(st.session_state.messages))


# ── Hero Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1>🇮🇳 Government Planning Assistant</h1>
    <p>Your AI companion for navigating Indian government welfare schemes</p>
    <div class="hero-badges">
        <span class="hero-badge">🤖 Powered by Gemini</span>
        <span class="hero-badge">📚 RAG Pipeline</span>
        <span class="hero-badge">🌏 10 Indian Languages</span>
        <span class="hero-badge">⚡ Real-time Answers</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Chat Area ────────────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div class="welcome-screen">
        <span class="welcome-icon">🏛️</span>
        <div class="welcome-title">Welcome! How can I help you today?</div>
        <p class="welcome-desc">
            Ask me anything about Indian government welfare schemes — PM-KISAN,
            Ayushman Bharat, PMAY, MGNREGA, PMJJBY and thousands more.
        </p>
        <div class="feature-chips">
            <div class="feature-chip">✅ Eligibility Check</div>
            <div class="feature-chip">📝 Application Guide</div>
            <div class="feature-chip">💰 Benefits Info</div>
            <div class="feature-chip">📄 Documents List</div>
        </div>
        <p class="welcome-hint">💬 Type below · or pull the <b style="color:#a5b4fc">tab on the left</b> for quick schemes →</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("sources"):
                chips = " ".join(f'<span class="source-chip">📄 {s}</span>' for s in msg["sources"][:4])
                st.markdown(chips, unsafe_allow_html=True)
            if msg.get("timestamp"):
                st.caption(f"🕐 {msg['timestamp']}")


# ── Input ────────────────────────────────────────────────────────────────────────
prefill = st.session_state.quick_question
st.session_state.quick_question = ""

user_input = st.chat_input(
    placeholder=f"✨ Ask about any government scheme in {st.session_state.lang_name}...",
    key="chat_input"
)
if prefill and not user_input:
    user_input = prefill


# ── Send ─────────────────────────────────────────────────────────────────────────
if user_input and user_input.strip():
    q  = user_input.strip()
    ts = datetime.now().strftime("%I:%M %p")

    with st.chat_message("user", avatar="🧑"):
        st.markdown(q)
        st.caption(f"🕐 {ts}")

    st.session_state.messages.append({"role":"user","content":q,"sources":[],"timestamp":ts})

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Searching scheme database..."):
            resp = send_chat(q, st.session_state.session_id, st.session_state.selected_lang)
        answer  = resp.get("answer","Sorry, could not process your question.")
        sources = resp.get("sources",[])
        bot_ts  = datetime.now().strftime("%I:%M %p")
        lang_tag = resp.get("detected_language", st.session_state.selected_lang).upper()
        st.markdown(answer)
        if sources:
            chips = " ".join(f'<span class="source-chip">📄 {s}</span>' for s in sources[:4])
            st.markdown(chips, unsafe_allow_html=True)
        st.caption(f"🕐 {bot_ts} · {lang_tag}")

    st.session_state.messages.append({"role":"assistant","content":answer,"sources":sources,"timestamp":f"{bot_ts} · {lang_tag}"})


# ── Footer ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:2rem 0 0.5rem;color:rgba(255,255,255,0.2);font-size:0.76rem">
    Built with ❤️ · LangChain · Gemini · ChromaDB · FastAPI · Streamlit<br>
    <span style="color:rgba(99,102,241,0.5)">Data sourced from official Indian Government portals</span>
</div>
""", unsafe_allow_html=True)
