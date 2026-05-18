"""
Paedia — AI-Powered Course Assistant
Streamlit UI Prototype — wired to Flask API via api_client.py
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)

Tech stack (Assessment 2): Flask WebApplication + Streamlit prototype UI,
LangChain orchestration, SentenceTransformers all-MiniLM-L6-v2 (384-dim),
ChromaDB (course_id scoped), PostgreSQL, Ollama (dev) + OpenAI (demo).
"""

import html as _html
import streamlit as st
import json
import os
import re
import time
from datetime import datetime
import random
from textwrap import dedent

from api_client import PaediaAPIClient, APIConfig

# ─── PAGE CONFIG ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Paedia — AI Course Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.stApp {
    background-color: #F8F9FA;
    color: #1A1A2E;
}

div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewContainer"] p,
div[data-testid="stAppViewContainer"] label,
div[data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] {
    color: #1A1A2E;
}

div[data-testid="stAppViewContainer"] h1,
div[data-testid="stAppViewContainer"] h2,
div[data-testid="stAppViewContainer"] h3,
div[data-testid="stAppViewContainer"] h4 {
    color: #1B2A4A;
}

section[data-testid="stSidebar"] {
    background-color: #0F1B33;
    border-right: 1px solid #1B2A4A;
}
section[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.4rem; color: #FFFFFF;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] .stCaption { color: #9AA0A6 !important; }
section[data-testid="stSidebar"] .stMarkdown strong { color: #D4A843 !important; }
section[data-testid="stSidebar"] button p { color: inherit !important; }

.user-msg {
    background: linear-gradient(135deg, #0D9488 0%, #0A7A6F 100%);
    color: white; padding: 14px 20px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0; max-width: 80%; float: right; clear: both;
    font-size: 0.95rem; line-height: 1.5;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.2);
}
.ai-msg {
    background: #FFFFFF; color: #1A1A2E;
    padding: 18px 22px; border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 85%; float: left; clear: both;
    font-size: 0.95rem; line-height: 1.6;
    border: 1px solid #E8EAED;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.ai-msg strong { color: #1B2A4A; }
.ai-msg code { background: #F1F3F4; padding: 2px 6px; border-radius: 4px; font-size: 0.88rem; }
.ai-msg-fallback {
    background: #FFFFFF; color: #1A1A2E;
    padding: 18px 22px; border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 85%; float: left; clear: both;
    font-size: 0.95rem; line-height: 1.6;
    border: 1px solid #F9AB00;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.fallback-label {
    display: inline-block; background: #FEF7E0; color: #B06000;
    padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;
    margin-bottom: 10px;
}

.source-chip {
    display: inline-block; background: #F1F3F4; border: 1px solid #E8EAED;
    border-radius: 16px; padding: 4px 14px; margin: 4px 6px 4px 0;
    font-size: 0.8rem; color: #5F6368; cursor: pointer; transition: all 0.2s;
}
.source-chip:hover { background: #E6F7F5; border-color: #0D9488; color: #0D9488; }
.source-label { font-size: 0.75rem; color: #9AA0A6; margin-top: 8px; margin-bottom: 4px; }

.confidence-bar { height: 6px; border-radius: 3px; margin-top: 12px; background: #E8EAED; overflow: hidden; }
.confidence-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }

.status-badge { display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
.badge-indexed { background: #E6F4EA; color: #137333; }
.badge-processing { background: #FEF7E0; color: #B06000; }
.badge-failed { background: #FCE8E6; color: #C5221F; }
.badge-pending { background: #F1F3F4; color: #5F6368; }
.badge-ready { background: #E6F4EA; color: #137333; }

.doc-card {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
    padding: 12px 16px; margin: 6px 0; display: flex; align-items: center; gap: 12px;
    transition: box-shadow 0.2s; color: #E8EAED;
}
.doc-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.2); }

.clearfix::after { content: ""; display: table; clear: both; }

#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

div[data-testid="stButton"] > button,
div[data-testid="stFormSubmitButton"] > button,
button[data-testid^="baseButton"] {
    min-height: 44px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
    opacity: 1 !important;
}

div[data-testid="stButton"] > button,
button[data-testid="baseButton-secondary"] {
    background: #FFFFFF !important;
    color: #1A1A2E !important;
    border: 1px solid #DADCE0 !important;
    box-shadow: 0 1px 2px rgba(15, 27, 51, 0.08) !important;
}

div[data-testid="stButton"] > button:hover,
button[data-testid="baseButton-secondary"]:hover {
    background: #E6F7F5 !important;
    color: #0A7A6F !important;
    border-color: #0D9488 !important;
}

div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background: #0D9488 !important;
    color: #FFFFFF !important;
    border: 1px solid #0D9488 !important;
    box-shadow: 0 2px 6px rgba(13, 148, 136, 0.22) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background: #0A7A6F !important;
    border-color: #0A7A6F !important;
}

div[data-testid="stButton"] > button *,
div[data-testid="stFormSubmitButton"] > button *,
button[data-testid^="baseButton"] * {
    color: inherit !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #E8ECF4 !important;
    border: 1px solid rgba(232, 236, 244, 0.14) !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    background: rgba(13, 148, 136, 0.18) !important;
    color: #FFFFFF !important;
    border-color: rgba(13, 148, 136, 0.55) !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
    background: #0D9488 !important;
    color: #FFFFFF !important;
    border-color: #0D9488 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button * {
    color: inherit !important;
    opacity: 1 !important;
}

.stTextInput > div > div > input {
    background: #FFFFFF !important;
    color: #1A1A2E !important;
    border-radius: 24px; padding: 12px 20px; border: 1px solid #E8EAED; font-size: 0.95rem;
}
.stTextInput > div > div > input::placeholder { color: #5F6368 !important; opacity: 1; }
.stTextInput > div > div > input:focus {
    border-color: #0D9488; box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15);
}

.stSelectbox div[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    color: #1A1A2E !important;
    border-color: #E8EAED !important;
}

div[data-testid="stMetric"] {
    background: white; border: 1px solid #E8EAED; border-radius: 12px;
    padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
div[data-testid="stMetric"] label { color: #5F6368 !important; font-size: 0.8rem !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1B2A4A !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)


# ─── LOAD DUMMY DATA ───────────────────────────────────────────────

def render_html(markup: str) -> None:
    """Render HTML without Markdown treating indented tags as code blocks."""
    cleaned = "\n".join(line.lstrip() for line in dedent(markup).strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


@st.cache_data
def load_responses():
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_responses.json")
    if os.path.exists(fixture_path):
        with open(fixture_path, "r") as f:
            return json.load(f)
    alt_path = os.path.join("fixtures", "sample_responses.json")
    if os.path.exists(alt_path):
        with open(alt_path, "r") as f:
            return json.load(f)
    return None


data = load_responses()


# ─── API CLIENT ───────────────────────────────────────────────────
# Connects to Flask WebApplication (Module 4) when available,
# otherwise falls back to fixture data for Sprint demos.

@st.cache_resource
def get_api_client():
    return PaediaAPIClient(APIConfig())

api = get_api_client()




# ─── SESSION STATE INIT ────────────────────────────────────────────

def init_session_state():
    defaults = {
        "authenticated": False,
        "jwt_token": None,
        "user": {},
        "messages": [],
        "current_page": "chat",
        "documents": data["documents"] if data else [],
        "session_history": [],
        "session_id": None,
        "course_id": None,
        "login_error": None,
        "pending_send": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ─── DUMMY BACKEND ──────────────────────────────────────────────────

def get_ai_response(query: str) -> dict:
    """
    Query the RAG pipeline via the API client.

    Flow: Streamlit → api_client.query() → Flask /api/query → VectorRetriever
    → LLMResponseGeneration → response with source_references.

    Falls back to fixture data (sample_responses.json) when the Flask API
    is unreachable (e.g. Task 2 not yet deployed).
    """
    course_id = st.session_state.get("course_id")
    session_id = st.session_state.get("session_id")
    return api.query(query, course_id=course_id or "", session_id=session_id)


def get_suggested_prompts() -> list:
    if data:
        return random.sample(data["suggested_prompts"], min(4, len(data["suggested_prompts"])))
    return ["Explain normalization", "What's on Week 5?", "Summarize lecture 3", "Quiz me on indexing"]


def get_default_course_id(user: dict) -> str:
    enrolled = user.get("enrolled_courses") or []
    if enrolled:
        return enrolled[0]
    if data and data.get("courses"):
        return data["courses"][0].get("course_id", "CSIT321")
    return "CSIT321"


# ─── LOGIN PAGE ─────────────────────────────────────────────────────

def render_login_page():
    # Centre the login card
    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown("""
        <div style="text-align: center; margin-top: 40px;">
            <div style="font-size: 2.5rem;">📚</div>
            <h2 style="color: #1B2A4A; margin: 8px 0 4px;">Paedia</h2>
            <p style="color: #5F6368;">AI-Powered Course Assistant</p>
            <p style="color: #9AA0A6; font-size: 0.8rem;">by Aletheia's Zetetes</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("#### Welcome back!")

        email = st.text_input("Email Address", placeholder="student@uow.edu.au", key="login_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

        if st.button("Sign In", type="primary", use_container_width=True):
            result = api.login(email, password)
            if result.get("success"):
                st.session_state.authenticated = True
                st.session_state.user = result.get("user", {})
                st.session_state.course_id = get_default_course_id(st.session_state.user)
                if result.get("jwt_token"):
                    st.session_state.jwt_token = result["jwt_token"]
                st.session_state.login_error = None
                st.rerun()
            else:
                st.session_state.login_error = result.get("error") or "Invalid email or password."
                st.rerun()

        st.markdown("""
        <div style="text-align: center; margin: 16px 0;">
            <span style="color: #9AA0A6; font-size: 0.85rem;">OR</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign in with UOW SSO", use_container_width=True):
            st.info("UOW SSO integration is not available in the prototype.")

        st.markdown("---")
        st.caption("CSIT321 Project 37 · Group 19 — Aletheia's Zetetes")

        st.markdown("""
        <div style="background: #F1F3F4; border-radius: 8px; padding: 12px 16px; margin-top: 16px; font-size: 0.82rem; color: #5F6368;">
            <strong>Demo accounts:</strong><br>
            Student: student@uow.edu.au / student123<br>
            Lecturer: lecturer@uow.edu.au / lecturer123<br>
            Admin: admin@uow.edu.au / admin123
        </div>
        """, unsafe_allow_html=True)


# ─── SIDEBAR ────────────────────────────────────────────────────────

def render_sidebar():
    role = st.session_state.user.get("role", "Student")

    with st.sidebar:
        st.markdown("# 📚 Paedia")
        st.caption("AI Course Assistant")
        st.divider()

        # Build nav based on role
        pages = {"chat": ("💬", "Q&A Chat"), "history": ("📋", "Session History")}

        if role in ("Lecturer", "Admin"):
            pages["doc_manager"] = ("📁", "Document Manager")
        else:
            pages["uploads"] = ("📁", "My Uploads")

        if role == "Admin":
            pages["admin"] = ("⚙️", "Admin Dashboard")

        for key, (icon, label) in pages.items():
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if st.session_state.current_page == key else "secondary",
            ):
                st.session_state.current_page = key
                st.rerun()

        st.divider()

        # Recent conversations
        if st.session_state.messages:
            st.markdown("**Recent Conversations**")
            queries = [m["content"][:35] + "..." for m in st.session_state.messages if m["role"] == "user"][-4:]
            for q in reversed(queries):
                st.markdown(f"<div style='background:#F1F3F4; padding:6px 12px; border-radius:6px; margin:4px 0; font-size:0.82rem; color:#5F6368;'>{_html.escape(q)}</div>", unsafe_allow_html=True)
            st.divider()

        # Loaded documents
        st.markdown("**Loaded Documents**")
        for doc in st.session_state.documents:
            doc_name = doc.get("filename", doc.get("name", "Unknown"))
            status_color = "#34A853" if doc["status"] == "indexed" else ("#F9AB00" if doc["status"] == "processing" else "#EA4335")
            st.markdown(
                f"<div class='doc-card'>"
                f"<span>📄</span>"
                f"<span style='flex:1; font-size:0.85rem;'>{_html.escape(str(doc_name))}</span>"
                f"<span style='width:10px; height:10px; border-radius:50%; background:{status_color}; display:inline-block;'></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        docs_count = len(st.session_state.documents)
        indexed = sum(1 for d in st.session_state.documents if d["status"] == "indexed")
        api_icon = "🟢" if api.is_live else "🟡"
        st.caption(f"{docs_count} docs loaded · {indexed} indexed · Semantic search ON")
        st.caption(f"{api_icon} {api.mode_label}")

        # User info + logout
        st.markdown("---")
        initials = "".join(w[0] for w in st.session_state.user.get("name", "U").split()[:2])
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(
                f"<div style='width:32px; height:32px; background:#0D9488; border-radius:50%; display:flex; align-items:center; justify-content:center; color:white; font-weight:600; font-size:0.8rem;'>{initials}</div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**{st.session_state.user.get('name', '')}**")
            st.caption(role)

        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ─── CHAT PAGE ──────────────────────────────────────────────────────

def _send_message(text: str):
    """Append a user message + AI response to the conversation."""
    st.session_state.messages.append({
        "role": "user",
        "content": text,
        "timestamp": datetime.now().strftime("%I:%M %p"),
    })
    response = get_ai_response(text)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"],
        "source_references": response.get("source_references", []),
        "confidence": response.get("confidence", 0),
        "model_used": response.get("model_used", "ollama/llama3"),
        "token_count": response.get("token_count", 0),
        "is_fallback": response.get("is_fallback", False),
        "from_api": response.get("from_api", False),
        "timestamp": datetime.now().strftime("%I:%M %p"),
    })


def render_chat_page():
    col1, col2, col3 = st.columns([5, 3, 2])
    with col1:
        st.markdown("### 💬 Ask your course materials")
    with col2:
        docs_count = len(st.session_state.documents)
        st.markdown(f"<span class='status-badge badge-ready'>{docs_count} docs indexed · Ready to answer</span>", unsafe_allow_html=True)
    with col3:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.markdown("<hr style='margin: 0 0 16px 0; border: none; border-top: 1px solid #E8EAED;'>", unsafe_allow_html=True)

    chat_container = st.container()

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 60px 20px; color: #9AA0A6;">
                <div style="font-size: 3rem; margin-bottom: 16px;">📚</div>
                <h3 style="color: #1A1A2E; margin-bottom: 8px;">Welcome to Paedia</h3>
                <p style="max-width: 500px; margin: 0 auto;">
                    Ask questions about your course materials and get AI-powered answers
                    grounded in your lecture slides, textbooks, and notes.
                </p>
            </div>
            """, unsafe_allow_html=True)

            prompts = get_suggested_prompts()
            cols = st.columns(len(prompts))
            for i, prompt in enumerate(prompts):
                with cols[i]:
                    if st.button(prompt, key=f"suggest_{i}", use_container_width=True):
                        _send_message(prompt)
                        st.rerun()
        else:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(f'<div class="clearfix"><div class="user-msg">{_html.escape(msg["content"])}</div></div>', unsafe_allow_html=True)
                else:
                    answer_html = _html.escape(msg["content"])
                    answer_html = answer_html.replace("\n", "<br>")
                    answer_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', answer_html)
                    answer_html = re.sub(r'`([^`]+)`', r'<code>\1</code>', answer_html)

                    is_fallback = msg.get("is_fallback", False)
                    fallback_html = ""
                    if is_fallback:
                        fallback_html = '<div class="fallback-label">⚠️ Based on general knowledge — not verified against course materials</div>'

                    sources_html = ""
                    if msg.get("source_references"):
                        sources_html = '<div class="source-label">Retrieved from:</div>'
                        for src in msg["source_references"]:
                            sources_html += f'<span class="source-chip">📄 {_html.escape(str(src.get("filename", "")))} · p.{src["page_number"]} · {int(src["similarity"] * 100)}%</span>'

                    confidence = msg.get("confidence", 0)
                    conf_color = "#34A853" if confidence > 0.8 else ("#D4A843" if confidence > 0.5 else "#EA4335")
                    conf_pct = int(confidence * 100)
                    model_used = _html.escape(msg.get("model_used", ""))
                    msg_class = "ai-msg-fallback" if is_fallback else "ai-msg"

                    render_html(f"""
                    <div class="clearfix"><div class="{msg_class}">
                        {fallback_html}
                        {answer_html}
                        {sources_html}
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {conf_pct}%; background: {conf_color};"></div>
                        </div>
                        <div style="font-size: 0.72rem; color: #9AA0A6; margin-top: 4px;">
                            Confidence: {conf_pct}% · {model_used} · {msg.get('timestamp', '')}{'  · 🟢 API' if msg.get('from_api') else ''}
                        </div>
                    </div></div>
                    """)

            st.markdown("<br>", unsafe_allow_html=True)
            prompts = get_suggested_prompts()
            cols = st.columns(len(prompts))
            for i, prompt in enumerate(prompts):
                with cols[i]:
                    if st.button(f"💡 {prompt}", key=f"followup_{i}", use_container_width=True):
                        _send_message(prompt)
                        st.rerun()

    # ── Input bar ──
    # FIX for issue #5: only submit on explicit button click, NOT on input change.
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([9, 1])
        with col1:
            user_input = st.text_input(
                "Ask a question",
                placeholder="Ask a question about your course materials...",
                label_visibility="collapsed",
                key="chat_input",
            )
        with col2:
            send_clicked = st.form_submit_button("➤", type="primary", use_container_width=True)

    if send_clicked and user_input and user_input.strip():
        with st.spinner("Searching course materials..."):
            time.sleep(0.5)
            _send_message(user_input.strip())
        st.rerun()


# ─── SESSION HISTORY PAGE ──────────────────────────────────────────

def render_history_page():
    st.markdown("### 📋 Session History")

    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.selectbox("Course", ["All courses", "CSIT321", "CSIT115", "ISIT312"], label_visibility="collapsed")
    with col2:
        st.selectbox("Period", ["Last 7 days", "Last 30 days", "All time"], label_visibility="collapsed")
    with col3:
        st.text_input("Search", placeholder="🔍 Search conversations...", label_visibility="collapsed")

    st.divider()

    sessions = [
        {"title": "RAG Pipeline Deep Dive", "course": "CSIT321", "time": "Today, 2:30 PM", "msgs": 8, "preview": "Asked about retrieval steps, embedding dimensions, and chunk overlap strategies..."},
        {"title": "Database Normalization", "course": "CSIT321", "time": "Today, 10:15 AM", "msgs": 5, "preview": "Explored 1NF through 3NF with examples, discussed denormalization trade-offs..."},
        {"title": "SQL Joins Overview", "course": "CSIT321", "time": "Yesterday, 4:45 PM", "msgs": 12, "preview": "Covered INNER, LEFT, RIGHT, FULL joins with visual diagrams and practice queries..."},
        {"title": "Week 5 Lecture Summary", "course": "CSIT321", "time": "Yesterday, 11:00 AM", "msgs": 3, "preview": "Quick summary of indexing concepts, B-trees, and hash indexes from Week 5..."},
        {"title": "ER Diagram Concepts", "course": "CSIT321", "time": "Apr 14, 9:20 AM", "msgs": 6, "preview": "Entity-relationship modeling, cardinality, participation constraints..."},
    ]
    accent_colors = ["#0D9488", "#1B2A4A", "#D4A843", "#0D9488", "#9AA0A6"]

    for i, session in enumerate(sessions):
        st.markdown(f"""
        <div style="background: white; border: 1px solid #E8EAED; border-radius: 12px; padding: 18px 24px; margin: 8px 0;
                    border-left: 4px solid {accent_colors[i]}; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-weight: 600; font-size: 1rem; color: #1A1A2E;">{session['title']}</span>
                    <span class="status-badge badge-ready" style="margin-left: 10px;">{session['course']}</span>
                </div>
                <span style="color: #9AA0A6; font-size: 0.82rem;">{session['time']}</span>
            </div>
            <p style="color: #5F6368; font-size: 0.88rem; margin: 8px 0;">{session['preview']}</p>
            <div style="display: flex; gap: 24px; align-items: center;">
                <span style="color: #9AA0A6; font-size: 0.8rem;">💬 {session['msgs']} messages</span>
                <span style="color: #9AA0A6; font-size: 0.8rem;">📄 3 sources cited</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([6, 1, 1])
        with col2:
            if st.button("Continue", key=f"continue_{i}"):
                st.session_state.current_page = "chat"
                st.rerun()
        with col3:
            st.button("Delete", key=f"delete_{i}", type="secondary")


# ─── UPLOADS PAGE (Student view — read-only list) ──────────────────

def render_uploads_page():
    st.markdown("### 📁 My Uploads")

    uploaded_files = st.file_uploader(
        "Upload course materials",
        type=["pdf", "pptx", "docx"],
        accept_multiple_files=True,
        help="Drag and drop PDF, PPTX, or DOCX files here",
    )

    if uploaded_files:
        for f in uploaded_files:
            st.success(f"✅ {f.name} received — indexing will begin once the backend is connected.")

    st.divider()
    st.markdown("**Uploaded Documents**")

    docs_data = [
        {"name": "Week3_Lecture_Normalisation.pdf", "type": "PDF", "size": "2.4 MB", "status": "Indexed", "uploaded": "15 Apr 2026"},
        {"name": "DatabaseNotes_Joins_Indexing.pptx", "type": "PPTX", "size": "5.1 MB", "status": "Indexed", "uploaded": "15 Apr 2026"},
        {"name": "Textbook_Ch9_QueryOptimisation.pdf", "type": "PDF", "size": "8.7 MB", "status": "Indexed", "uploaded": "14 Apr 2026"},
    ]

    cols = st.columns([4, 1, 1, 1, 2, 1])
    for col, header in zip(cols, ["File Name", "Type", "Size", "Status", "Uploaded", "Actions"]):
        col.markdown(f"**{header}**")

    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E8EAED;'>", unsafe_allow_html=True)

    for doc in docs_data:
        cols = st.columns([4, 1, 1, 1, 2, 1])
        cols[0].markdown(f"📄 {doc['name']}")
        cols[1].markdown(doc["type"])
        cols[2].markdown(doc["size"])
        cols[3].markdown(f"<span class='status-badge badge-indexed'>{doc['status']}</span>", unsafe_allow_html=True)
        cols[4].markdown(doc["uploaded"])
        cols[5].button("🗑️", key=f"del_{doc['name']}")

    st.divider()
    st.caption(f"{len(docs_data)} documents · {len(docs_data)} indexed · Semantic search ON")


# ─── DOCUMENT MANAGER (Lecturer / Admin view) ──────────────────────

def render_doc_manager_page():
    st.markdown("### 📁 Document Manager")
    role = st.session_state.user.get("role", "Student")
    st.markdown(f"<span class='status-badge badge-processing'>{role} View</span>", unsafe_allow_html=True)

    # Upload area
    uploaded_files = st.file_uploader(
        "Upload course materials",
        type=["pdf", "pptx", "docx"],
        accept_multiple_files=True,
        help="Drag and drop PDF, PPTX, or DOCX files here. Max 50 MB per file.",
    )

    col1, col2, col3 = st.columns([3, 3, 2])
    with col1:
        selected_course = st.selectbox(
            "Course",
            ["CSIT321", "CSIT214", "ISIT312"],
            label_visibility="collapsed",
            format_func=lambda c: {"CSIT321": "CSIT321 - Project Development", "CSIT214": "CSIT214 - Database Systems", "ISIT312": "ISIT312 - Big Data"}.get(c, c),
        )
    with col3:
        do_upload = st.button("Upload & Index", type="primary", use_container_width=True)

    if uploaded_files and do_upload:
        for f in uploaded_files:
            file_bytes = f.read()
            result = api.upload_document(file_bytes, f.name, selected_course)
            if result.get("success"):
                doc = result.get("document", {})
                job_id = doc.get("indexing_job_id", "")
                st.success(f"✅ {f.name} queued for indexing.{' Job ID: ' + job_id[:8] + '…' if job_id else ''}")
            else:
                st.error(f"❌ {f.name} upload failed: {result.get('error', 'unknown error')}")
    elif uploaded_files:
        for f in uploaded_files:
            st.info(f"📄 {f.name} staged — click Upload & Index to submit.")

    st.divider()
    st.markdown("**UPLOADED DOCUMENTS**")

    docs_data = [
        {"name": "Week3_Lecture_Normalisation.pdf", "type": "PDF", "size": "2.4 MB", "status": "Indexed", "uploaded": "15 Apr 2026"},
        {"name": "DatabaseNotes_Joins_Indexing.pptx", "type": "PPTX", "size": "5.1 MB", "status": "Indexed", "uploaded": "15 Apr 2026"},
        {"name": "Textbook_Ch9_QueryOptimisation.pdf", "type": "PDF", "size": "8.7 MB", "status": "Indexed", "uploaded": "14 Apr 2026"},
        {"name": "Week5_Indexing_QueryPlans.docx", "type": "DOCX", "size": "1.1 MB", "status": "Processing", "uploaded": "20 Apr 2026"},
        {"name": "RAG_Pipeline_Overview.pdf", "type": "PDF", "size": "1.8 MB", "status": "Indexed", "uploaded": "13 Apr 2026"},
    ]

    cols = st.columns([4, 1, 1, 1, 2, 1])
    for col, header in zip(cols, ["File Name", "Type", "Size", "Status", "Uploaded", "Actions"]):
        col.markdown(f"**{header}**")
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E8EAED;'>", unsafe_allow_html=True)

    for doc in docs_data:
        cols = st.columns([4, 1, 1, 1, 2, 1])
        cols[0].markdown(f"📄 {doc['name']}")
        cols[1].markdown(doc["type"])
        cols[2].markdown(doc["size"])
        badge_class = "badge-indexed" if doc["status"] == "Indexed" else ("badge-processing" if doc["status"] == "Processing" else "")
        badge_style = "background: #FCE8E6; color: #C5221F;" if doc["status"] == "Failed" else ""
        cols[3].markdown(f"<span class='status-badge {badge_class}' style='{badge_style}'>{doc['status']}</span>", unsafe_allow_html=True)
        cols[4].markdown(doc["uploaded"])
        c1, c2 = cols[5].columns(2)
        c1.button("🔄", key=f"retry_{doc['name']}")
        c2.button("🗑️", key=f"delmgr_{doc['name']}")

    st.divider()
    indexed = sum(1 for d in docs_data if d["status"] == "Indexed")
    processing = sum(1 for d in docs_data if d["status"] == "Processing")
    failed = sum(1 for d in docs_data if d["status"] == "Failed")
    st.caption(f"{len(docs_data)} documents · {indexed} indexed · {processing} processing · {failed} failed")


# ─── ADMIN DASHBOARD (Admin only) ──────────────────────────────────

def render_admin_page():
    st.markdown("### ⚙️ Admin Dashboard")
    st.markdown("<span class='status-badge' style='background:#FCE8E6; color:#C5221F;'>Admin</span>", unsafe_allow_html=True)

    # Stats cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Users", "142", "↑ 12 this week")
    c2.metric("Documents", "38", "5 courses")
    c3.metric("Queries Today", "87", "↑ 23%")
    c4.metric("Avg Response", "1.2s", "within target")

    st.divider()
    st.markdown("#### User Management")

    col1, col2 = st.columns([4, 2])
    with col1:
        st.text_input("Search", placeholder="🔍 Search users...", label_visibility="collapsed", key="admin_search")
    with col2:
        st.button("+ Add User", type="primary", use_container_width=True)

    users = [
        {"name": "Anmoldeep Singh", "email": "anmoldeep@uow.edu.au", "role": "Student", "last": "2 hrs ago", "queries": 34, "status": "Active"},
        {"name": "Prof. Jun Yan", "email": "junyan@uow.edu.au", "role": "Lecturer", "last": "1 hr ago", "queries": 12, "status": "Active"},
        {"name": "Sarah Chen", "email": "schen@uow.edu.au", "role": "Student", "last": "5 hrs ago", "queries": 28, "status": "Active"},
        {"name": "Admin User", "email": "admin@uow.edu.au", "role": "Admin", "last": "Just now", "queries": 5, "status": "Active"},
    ]

    cols = st.columns([3, 2, 2, 1, 1, 2])
    for col, header in zip(cols, ["User", "Role", "Last Active", "Queries", "Status", "Actions"]):
        col.markdown(f"**{header}**")
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E8EAED;'>", unsafe_allow_html=True)

    for u in users:
        cols = st.columns([3, 2, 2, 1, 1, 2])
        cols[0].markdown(f"**{u['name']}**<br><span style='color:#9AA0A6; font-size:0.8rem;'>{u['email']}</span>", unsafe_allow_html=True)
        role_color = "#1B2A4A" if u["role"] == "Admin" else ("#0D9488" if u["role"] == "Lecturer" else "#9AA0A6")
        cols[1].markdown(f"<span class='status-badge' style='background:{role_color}20; color:{role_color};'>{u['role']}</span>", unsafe_allow_html=True)
        cols[2].markdown(u["last"])
        cols[3].markdown(str(u["queries"]))
        cols[4].markdown(f"<span class='status-badge badge-indexed'>{u['status']}</span>", unsafe_allow_html=True)
        c_edit, c_del = cols[5].columns(2)
        c_edit.button("Edit", key=f"edit_{u['email']}")
        c_del.button("Del", key=f"delusr_{u['email']}")

    st.divider()
    st.markdown("#### System Settings")

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown("**LLM Provider**")
        st.selectbox("LLM", ["Ollama (dev)", "OpenAI API (demo)"], label_visibility="collapsed", key="llm_model")
    with s2:
        st.markdown("**Embedding Model**")
        st.selectbox("Embed", ["all-MiniLM-L6-v2 (384-dim)", "all-mpnet-base-v2 (768-dim)"], label_visibility="collapsed", key="embed_model")
    with s3:
        st.markdown("**Vector Store**")
        st.selectbox("VDB", ["ChromaDB (course_id scoped)"], label_visibility="collapsed", key="vector_db")
    with s4:
        st.markdown("**Chunk Size**")
        st.selectbox("Chunk", ["1024 tokens / 0 overlap", "512 tokens / 0 overlap", "256 tokens / 0 overlap"], label_visibility="collapsed", key="chunk_size")

    s5, s6, s7, s8 = st.columns(4)
    with s5:
        st.markdown("**Orchestration**")
        st.selectbox("Orch", ["LangChain", "LlamaIndex"], label_visibility="collapsed", key="orch_framework")
    with s6:
        st.markdown("**Relational DB**")
        st.selectbox("RDB", ["PostgreSQL"], label_visibility="collapsed", key="relational_db")
    with s7:
        st.markdown("**Top-k Retrieval**")
        st.selectbox("Top-k", ["5", "3", "10"], label_visibility="collapsed", key="top_k")
    with s8:
        st.markdown("**Deployment**")
        st.selectbox("Deploy", ["Docker Compose (local)"], label_visibility="collapsed", key="deployment")


# ─── MAIN APP ───────────────────────────────────────────────────────

def main():
    # Gate: show login if not authenticated
    if not st.session_state.authenticated:
        render_login_page()
        return

    render_sidebar()

    page = st.session_state.current_page
    role = st.session_state.user.get("role", "Student")

    if page == "chat":
        render_chat_page()
    elif page == "history":
        render_history_page()
    elif page == "uploads":
        render_uploads_page()
    elif page == "doc_manager" and role in ("Lecturer", "Admin"):
        render_doc_manager_page()
    elif page == "admin" and role == "Admin":
        render_admin_page()
    else:
        # Fallback: if page isn't available for role, go to chat
        st.session_state.current_page = "chat"
        st.rerun()


if __name__ == "__main__":
    main()