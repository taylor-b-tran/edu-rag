"""
Paedia — AI-Powered Course Assistant
Streamlit UI Prototype — wired to Flask API via api_client.py
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)

Sprint 5 updates:
  S5-T09: Fixed readability/contrast — all text visible, buttons readable
  S5-T10: Connected query flow to backend evidence — ChromaDB metadata, model info, error states
  S5-T11: Improved upload + history flow — timestamps, query state, session management
"""

import streamlit as st
import json
import os
import re
import time
import uuid
from datetime import datetime
import random

from api_client import PaediaAPIClient, APIConfig

# ─── PAGE CONFIG ────────────────────────────────────────────────────

st.set_page_config(
    page_title="Paedia — AI Course Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS (T09: readability & contrast fixes) ────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #F8F9FA; }

/* ── Main area text visibility (handles dark mode browser overrides) ── */
.stApp [data-testid="stMain"] .stMarkdown p,
.stApp [data-testid="stMain"] .stMarkdown li,
.stApp [data-testid="stMain"] .stMarkdown span,
.stApp [data-testid="stMain"] .stMarkdown label,
.stApp [data-testid="stMain"] .stMarkdown div,
.stApp [data-testid="stMain"] h1,
.stApp [data-testid="stMain"] h2,
.stApp [data-testid="stMain"] h3,
.stApp [data-testid="stMain"] h4,
.stApp [data-testid="stMain"] h5,
.stApp [data-testid="stMain"] h6,
.stApp [data-testid="stMain"] label,
.stApp [data-testid="stMain"] p,
.stApp [data-testid="stMain"] span,
.stApp [data-testid="stMain"] li,
.stApp [data-testid="stMain"] small,
.stApp [data-testid="stMain"] .stCaption {
    color: #1E293B !important;
}

/* ── Selectbox and popovers dropdowns styling to ensure readable text ── */
div[data-baseweb="select"] {
    color: #1B2A4A !important;
    background: #FFFFFF !important;
}
div[data-baseweb="popover"] * {
    color: #1B2A4A !important;
    background-color: #FFFFFF !important;
}
div[role="listbox"] * {
    background-color: #FFFFFF !important;
    color: #1B2A4A !important;
}

/* ── Sidebar — navy bg, ensure ALL text is readable ── */
section[data-testid="stSidebar"] {
    background-color: #0F1B33;
    border-right: 1px solid #1B2A4A;
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown h4 {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] .stMarkdown div {
    color: #CBD5E1 !important;
}
section[data-testid="stSidebar"] .stMarkdown strong {
    color: #D4A843 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
}

/* ── Sidebar buttons — readable text on all states ── */
section[data-testid="stSidebar"] .stButton > button {
    color: #E2E8F0 !important;
    background-color: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background-color: #0D9488 !important;
    color: #FFFFFF !important;
    border-color: #0D9488 !important;
}

/* ── Main area buttons — ensure text visible ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
    color: #1B2A4A !important;
    border: 1px solid #E2E8F0 !important;
}
.stButton > button:hover {
    border-color: #0D9488 !important;
    color: #0D9488 !important;
}
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background-color: #0D9488 !important;
    color: #FFFFFF !important;
    border-color: #0D9488 !important;
}
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #0A7A70 !important;
}

/* ── Form inputs — visible borders, labels, focus states ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1.5px solid #CBD5E1 !important;
    color: #1B2A4A !important;
    background: #FFFFFF !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0D9488 !important;
    box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.15) !important;
}
.stTextInput > label, .stTextArea > label, .stSelectbox > label,
.stFileUploader > label {
    color: #334155 !important;
    font-weight: 500 !important;
}

/* ── Chat bubbles ── */
.user-msg {
    background: linear-gradient(135deg, #0D9488 0%, #0A7A6F 100%);
    color: #FFFFFF; padding: 14px 20px;
    border-radius: 18px 18px 4px 18px;
    margin: 8px 0; max-width: 80%; float: right; clear: both;
    font-size: 0.95rem; line-height: 1.5;
    box-shadow: 0 2px 8px rgba(13, 148, 136, 0.2);
}
.user-msg .msg-time { color: rgba(255,255,255,0.7); font-size: 0.72rem; margin-top: 6px; }

.ai-msg {
    background: #FFFFFF; color: #1E293B;
    padding: 18px 22px; border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 85%; float: left; clear: both;
    font-size: 0.95rem; line-height: 1.6;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.ai-msg strong { color: #1B2A4A; }
.ai-msg code { background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-size: 0.88rem; color: #334155; }
.ai-msg .msg-time { color: #94A3B8; font-size: 0.72rem; margin-top: 6px; }

.ai-msg-fallback {
    background: #FFFBEB; color: #1E293B;
    padding: 18px 22px; border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 85%; float: left; clear: both;
    font-size: 0.95rem; line-height: 1.6;
    border: 2px solid #D4A843;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.ai-msg-fallback .msg-time { color: #94A3B8; font-size: 0.72rem; margin-top: 6px; }

.fallback-label {
    display: inline-flex; align-items: center; gap: 6px;
    background: #FEF3C7; color: #92400E;
    padding: 6px 14px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;
    margin-bottom: 10px; border: 1px solid #FCD34D;
}

.error-card {
    background: #FEF2F2; color: #991B1B;
    padding: 16px 20px; border-radius: 12px;
    border: 1px solid #FECACA;
    margin: 12px 0;
}
.error-card strong { color: #7F1D1D; }

/* ── Source chips — readable on hover ── */
.source-chip {
    display: inline-block; background: #F1F5F9; border: 1px solid #E2E8F0;
    border-radius: 16px; padding: 5px 14px; margin: 4px 6px 4px 0;
    font-size: 0.8rem; color: #475569; cursor: pointer; transition: all 0.2s;
}
.source-chip:hover { background: #CCFBF1; border-color: #0D9488; color: #0D9488; }
.source-label { font-size: 0.75rem; color: #64748B; margin-top: 8px; margin-bottom: 4px; font-weight: 500; }

/* ── Confidence bar ── */
.confidence-bar { height: 6px; border-radius: 3px; margin-top: 12px; background: #E2E8F0; overflow: hidden; }
.confidence-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
.confidence-text { font-size: 0.75rem; color: #64748B; margin-top: 4px; }

/* ── Model badge ── */
.model-badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 600;
}
.model-ollama { background: #DBEAFE; color: #1E40AF; }
.model-openai { background: #D1FAE5; color: #065F46; }
.model-unknown { background: #F1F5F9; color: #475569; }

/* ── Status badges ── */
.status-badge { display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
.badge-indexed { background: #D1FAE5; color: #065F46; }
.badge-processing { background: #FEF3C7; color: #92400E; }
.badge-failed { background: #FEE2E2; color: #991B1B; }
.badge-pending { background: #F1F5F9; color: #475569; }
.badge-ready { background: #D1FAE5; color: #065F46; }

/* ── Upload progress ── */
.upload-progress {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 16px 20px; margin: 8px 0;
}
.upload-step { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 0.85rem; }
.upload-step-done { color: #065F46; }
.upload-step-active { color: #0D9488; font-weight: 600; }
.upload-step-pending { color: #94A3B8; }

/* ── Session card (sidebar) ── */
.session-card {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 8px 12px; margin: 4px 0; cursor: pointer;
    transition: all 0.2s; color: #CBD5E1;
}
.session-card:hover { background: rgba(255,255,255,0.1); }
.session-card-active { border-color: #0D9488; background: rgba(13,148,136,0.15); }
.session-card .session-title { font-size: 0.82rem; font-weight: 500; color: #E2E8F0; }
.session-card .session-meta { font-size: 0.72rem; color: #94A3B8; margin-top: 2px; }

/* ── Doc card (sidebar) ── */
.doc-card {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
    padding: 10px 14px; margin: 6px 0; display: flex; align-items: center; gap: 10px;
    transition: all 0.2s; color: #CBD5E1;
}
.doc-card:hover { background: rgba(255,255,255,0.1); }

/* ── Retrieval details ── */
.retrieval-details {
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 12px 16px; margin-top: 8px; font-size: 0.8rem; color: #475569;
}
.retrieval-details strong { color: #1E293B; }
.retrieval-details .detail-row { display: flex; justify-content: space-between; padding: 3px 0; }

/* ── Metrics ── */
div[data-testid="stMetric"] {
    background: white; border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
div[data-testid="stMetric"] label { color: #64748B !important; font-size: 0.8rem !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #1B2A4A !important; font-weight: 700 !important; }

/* ── Query state indicator ── */
.query-state {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 16px; background: #F0FDFA; border: 1px solid #99F6E4;
    border-radius: 12px; margin: 8px 0; color: #0D9488; font-size: 0.88rem; font-weight: 500;
}
.query-state .dot { width: 8px; height: 8px; border-radius: 50%; background: #0D9488; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.clearfix::after { content: ""; display: table; clear: both; }

#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── LOAD FIXTURE DATA ────────────────────────────────────────────

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

@st.cache_resource
def get_api_client():
    return PaediaAPIClient(APIConfig())

api = get_api_client()
DEFAULT_COURSE_ID = "CSIT321"
COURSE_FALLBACKS = [DEFAULT_COURSE_ID, "CSIT214"]


# ─── DEMO CREDENTIALS ──────────────────────────────────────────────

DEMO_USERS = {
    "student@uow.edu.au": {
        "password": "student123",
        "name": "Anmoldeep Singh",
        "email": "student@uow.edu.au",
        "role": "Student",
        "id": "8443580",
    },
    "lecturer@uow.edu.au": {
        "password": "lecturer123",
        "name": "Prof. Jun Yan",
        "email": "lecturer@uow.edu.au",
        "role": "Lecturer",
        "id": "1001",
    },
    "admin@uow.edu.au": {
        "password": "admin123",
        "name": "Admin User",
        "email": "admin@uow.edu.au",
        "role": "Admin",
        "id": "0001",
    },
}


# ─── SESSION STATE INIT ────────────────────────────────────────────

def _normalise_user_for_ui(user: dict) -> dict:
    ui_user = dict(user or {})
    role = str(ui_user.get("role", "student"))
    role_map = {"student": "Student", "lecturer": "Lecturer", "admin": "Admin"}
    ui_user["role"] = role_map.get(role.lower(), role)
    ui_user["id"] = ui_user.get("id") or ui_user.get("user_id") or ui_user.get("username") or ""
    return ui_user


def _course_options_for_user(user: dict) -> list[str]:
    courses = data.get("courses", []) if data else []
    enrolled = set(user.get("enrolled_courses", []) or [])
    role = str(user.get("role", "")).lower()
    options: list[str] = []
    for course in courses:
        code = course.get("course_code") or course.get("course_id")
        course_id = course.get("course_id")
        if not code:
            continue
        if role == "admin" or course_id in enrolled or code in enrolled:
            options.append(code)
    if not options:
        options = [c for c in COURSE_FALLBACKS if c]
    return list(dict.fromkeys(options))


def _default_course_for_user(user: dict) -> str:
    options = _course_options_for_user(user)
    return DEFAULT_COURSE_ID if DEFAULT_COURSE_ID in options else options[0]


def init_session_state():
    defaults = {
        "authenticated": False,
        "jwt_token": None,
        "user": {},
        "messages": [],
        "current_page": "chat",
        "documents": data["documents"] if data else [],
        "session_history": [],
        "sessions": [],
        "active_session_id": None,
        "session_id": None,
        "course_id": DEFAULT_COURSE_ID,
        "course_options": COURSE_FALLBACKS,
        "selected_course_id": DEFAULT_COURSE_ID,
        "login_error": None,
        "pending_send": False,
        "query_state": None,
        "upload_progress": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ─── HELPER: SESSION MANAGEMENT (T11) ─────────────────────────────

def create_new_session(title="New Chat"):
    """Create a new chat session and make it active."""
    course_id = st.session_state.get("course_id") or DEFAULT_COURSE_ID
    session = {
        "session_id": str(uuid.uuid4())[:8],
        "backend_session_id": None,
        "title": title,
        "messages": [],
        "course_id": course_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message_count": 0,
    }
    st.session_state.sessions.append(session)
    st.session_state.active_session_id = session["session_id"]
    st.session_state.session_id = None
    st.session_state.course_id = course_id
    st.session_state.selected_course_id = course_id
    st.session_state.messages = session["messages"]
    return session


def get_active_session():
    """Return the active session, creating one if needed."""
    if not st.session_state.sessions:
        return create_new_session()
    for s in st.session_state.sessions:
        if s["session_id"] == st.session_state.active_session_id:
            return s
    return st.session_state.sessions[-1]


def switch_session(session_id):
    """Switch to a different chat session."""
    for s in st.session_state.sessions:
        if s["session_id"] == session_id:
            st.session_state.active_session_id = session_id
            st.session_state.messages = s["messages"]
            st.session_state.session_id = s.get("backend_session_id")
            st.session_state.course_id = s.get("course_id", DEFAULT_COURSE_ID)
            st.session_state.selected_course_id = st.session_state.course_id
            return


# ─── RAG QUERY ─────────────────────────────────────────────────────

def get_ai_response(query: str) -> dict:
    """Query the RAG pipeline via the API client."""
    course_id = st.session_state.get("course_id") or DEFAULT_COURSE_ID
    session_id = st.session_state.get("session_id")
    return api.query(query, course_id=course_id, session_id=session_id)


def get_suggested_prompts() -> list:
    fallback = ["Explain normalization", "What's on Week 5?", "Summarize lecture 3", "Quiz me on indexing"]
    prompts = data.get("suggested_prompts", fallback) if data else fallback
    return random.sample(prompts, min(4, len(prompts)))


def get_model_badge(model_used: str) -> str:
    """Return HTML badge for the LLM model used (T10)."""
    if "ollama" in model_used.lower():
        return f'<span class="model-badge model-ollama">🦙 {model_used}</span>'
    elif "openai" in model_used.lower() or "gpt" in model_used.lower():
        return f'<span class="model-badge model-openai">🤖 {model_used}</span>'
    return f'<span class="model-badge model-unknown">🔧 {model_used}</span>'


def _confidence_score(confidence, confidence_score=None) -> float:
    if isinstance(confidence_score, (int, float)):
        return max(0.0, min(float(confidence_score), 1.0))
    if isinstance(confidence, (int, float)):
        return max(0.0, min(float(confidence), 1.0))
    if isinstance(confidence, str):
        label_scores = {"high": 0.9, "medium": 0.6, "low": 0.3}
        lowered = confidence.lower()
        if lowered in label_scores:
            return label_scores[lowered]
        try:
            return max(0.0, min(float(confidence), 1.0))
        except ValueError:
            return 0.0
    return 0.0


def get_confidence_label(confidence) -> str:
    """Return human-readable confidence label."""
    if isinstance(confidence, str) and confidence.lower() in {"high", "medium", "low"}:
        return f"{confidence.capitalize()} confidence"
    confidence = _confidence_score(confidence)
    if confidence >= 0.8:
        return "High confidence"
    elif confidence >= 0.5:
        return "Medium confidence"
    elif confidence > 0:
        return "Low confidence"
    return "No confidence data"


# ─── LOGIN PAGE ─────────────────────────────────────────────────────

def render_login_page():
    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown("""
        <div style="text-align: center; margin-top: 40px;">
            <div style="font-size: 2.5rem;">📚</div>
            <h2 style="color: #1B2A4A; margin: 8px 0 4px;">Paedia</h2>
            <p style="color: #475569;">AI-Powered Course Assistant</p>
            <p style="color: #94A3B8; font-size: 0.8rem;">by Aletheia's Zetetes</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("#### Welcome back!")

        email = st.text_input("Email Address", placeholder="student@uow.edu.au", key="login_email")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

        if st.button("Sign In", type="primary", use_container_width=True):
            login_result = api.login(email.strip(), password)
            if login_result.get("success"):
                user = _normalise_user_for_ui(login_result.get("user", {}))
                st.session_state.authenticated = True
                st.session_state.jwt_token = login_result.get("jwt_token")
                st.session_state.user = user
                st.session_state.course_options = _course_options_for_user(user)
                st.session_state.course_id = _default_course_for_user(user)
                st.session_state.selected_course_id = st.session_state.course_id
                st.session_state.login_error = None
                create_new_session("Welcome Chat")
                st.rerun()
            elif login_result.get("use_demo_auth"):
                user = DEMO_USERS.get(email.strip())
                if user and user["password"] == password:
                    user = _normalise_user_for_ui({k: v for k, v in user.items() if k != "password"})
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.session_state.course_options = _course_options_for_user(user)
                    st.session_state.course_id = _default_course_for_user(user)
                    st.session_state.selected_course_id = st.session_state.course_id
                    st.session_state.login_error = None
                    create_new_session("Welcome Chat")
                    st.rerun()
                else:
                    st.session_state.login_error = "Invalid email or password. Try student@uow.edu.au / student123"
                    st.rerun()
            else:
                st.session_state.login_error = login_result.get("error") or "Invalid email or password."
                st.rerun()

        st.markdown("""
        <div style="text-align: center; margin: 16px 0;">
            <span style="color: #94A3B8; font-size: 0.85rem;">OR</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Sign in with UOW SSO", use_container_width=True):
            st.info("UOW SSO integration is not available in the prototype.")

        st.markdown("---")
        st.caption("CSIT321 Project 37 · Group 19 — Aletheia's Zetetes")

        st.markdown("""
        <div style="background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 16px; margin-top: 16px; font-size: 0.82rem; color: #475569;">
            <strong style="color: #1E293B;">Demo accounts:</strong><br>
            <span style="color: #334155;">Student:</span> student@uow.edu.au / student123<br>
            <span style="color: #334155;">Lecturer:</span> lecturer@uow.edu.au / lecturer123<br>
            <span style="color: #334155;">Admin:</span> admin@uow.edu.au / admin123
        </div>
        """, unsafe_allow_html=True)


# ─── SIDEBAR (T09: readability + T11: session management) ─────────

def render_sidebar():
    role = st.session_state.user.get("role", "Student")

    with st.sidebar:
        st.markdown("# 📚 Paedia")
        st.caption("AI Course Assistant")
        st.divider()

        # Navigation buttons
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

        # ── Session list (T11) ──
        st.markdown("**Chat Sessions**")
        if st.button("➕ New Chat", key="new_chat_btn", use_container_width=True):
            create_new_session()
            st.session_state.current_page = "chat"
            st.rerun()

        for s in reversed(st.session_state.sessions[-5:]):
            is_active = s["session_id"] == st.session_state.active_session_id
            card_class = "session-card session-card-active" if is_active else "session-card"
            title = s["title"][:30] + ("..." if len(s["title"]) > 30 else "")
            msg_count = len(s.get("messages", []))
            st.markdown(
                f"<div class='{card_class}'>"
                f"<div class='session-title'>💬 {title}</div>"
                f"<div class='session-meta'>{msg_count} msgs · {s.get('created_at', '')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if not is_active:
                if st.button(f"Switch", key=f"switch_{s['session_id']}", use_container_width=True):
                    switch_session(s["session_id"])
                    st.session_state.current_page = "chat"
                    st.rerun()

        st.divider()

        # ── Loaded documents ──
        st.markdown("**Loaded Documents**")
        for doc in st.session_state.documents[:5]:
            doc_name = doc.get("filename", doc.get("name", "Unknown"))
            status = doc.get("status", "pending")
            status_color = "#10B981" if status == "indexed" else ("#F59E0B" if status == "processing" else "#EF4444")
            st.markdown(
                f"<div class='doc-card'>"
                f"<span>📄</span>"
                f"<span style='flex:1; font-size:0.82rem; color: #CBD5E1;'>{doc_name}</span>"
                f"<span style='width:10px; height:10px; border-radius:50%; background:{status_color}; display:inline-block;'></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        docs_count = len(st.session_state.documents)
        indexed = sum(1 for d in st.session_state.documents if d.get("status") == "indexed")
        api_icon = "🟢" if api.is_live else "🟡"
        st.caption(f"{docs_count} docs loaded · {indexed} indexed · Semantic search ON")
        st.caption(f"{api_icon} {api.mode_label}")

        # ── User info + logout ──
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
            api.clear_auth()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


# ─── CHAT PAGE (T09+T10+T11: full overhaul) ───────────────────────

def _send_message(text: str):
    """Append a user message + AI response with full metadata."""
    now = datetime.now()
    st.session_state.messages.append({
        "role": "user",
        "content": text,
        "timestamp": now.strftime("%I:%M %p"),
        "timestamp_full": now.isoformat(),
    })

    # Update session title from first query
    session = get_active_session()
    if session and session["title"] in ("New Chat", "Welcome Chat") and len(session["messages"]) <= 2:
        session["title"] = text[:40] + ("..." if len(text) > 40 else "")

    response = get_ai_response(text)
    now2 = datetime.now()
    backend_session_id = response.get("session_id")
    if backend_session_id:
        st.session_state.session_id = backend_session_id
        if session:
            session["backend_session_id"] = backend_session_id
            session["course_id"] = st.session_state.get("course_id") or DEFAULT_COURSE_ID

    msg = {
        "role": "assistant",
        "content": response.get("answer", ""),
        "source_references": response.get("source_references", []),
        "confidence": response.get("confidence", 0),
        "confidence_score": response.get("confidence_score"),
        "model_used": response.get("model_used", "ollama/llama3"),
        "token_count": response.get("token_count", 0),
        "is_fallback": response.get("is_fallback", False),
        "from_api": response.get("from_api", False),
        "backend_mode": response.get("backend_mode"),
        "retrieval_metadata": response.get("retrieval_metadata"),
        "error_type": response.get("error_type"),
        "error_message": response.get("error_message"),
        "timestamp": now2.strftime("%I:%M %p"),
        "timestamp_full": now2.isoformat(),
    }
    st.session_state.messages.append(msg)

    # Update session message count
    if session:
        session["message_count"] = len(session["messages"])


def render_chat_page():
    session = get_active_session()

    col1, col2, col3, col4 = st.columns([5, 3, 2, 2])
    with col1:
        st.markdown("### 💬 Ask your course materials")
    with col2:
        docs_count = len(st.session_state.documents)
        model_label = "ollama/llama3" if not api.is_live else "Live API"
        st.markdown(
            f"<span class='status-badge badge-ready'>{docs_count} docs indexed</span> "
            f"{get_model_badge(model_label)}",
            unsafe_allow_html=True,
        )
    with col3:
        course_options = st.session_state.get("course_options") or COURSE_FALLBACKS
        current_course = st.session_state.get("course_id") or DEFAULT_COURSE_ID
        if current_course not in course_options:
            course_options = [current_course] + list(course_options)
        selected_course = st.selectbox(
            "Course",
            course_options,
            index=course_options.index(current_course),
            label_visibility="collapsed",
            key="selected_course_id",
        )
    if selected_course != st.session_state.get("course_id"):
        st.session_state.course_id = selected_course
        st.session_state.session_id = None
        if session:
            session["course_id"] = selected_course
            session["backend_session_id"] = None
    with col4:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = None
            if session:
                session["messages"] = []
                session["message_count"] = 0
                session["backend_session_id"] = None
            st.rerun()

    st.markdown("<hr style='margin: 0 0 16px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    chat_container = st.container()

    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 60px 20px; color: #64748B;">
                <div style="font-size: 3rem; margin-bottom: 16px;">📚</div>
                <h3 style="color: #1E293B; margin-bottom: 8px;">Welcome to Paedia</h3>
                <p style="max-width: 500px; margin: 0 auto; color: #475569;">
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
                timestamp_str = msg.get("timestamp", "")

                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="clearfix"><div class="user-msg">'
                        f'{msg["content"]}'
                        f'<div class="msg-time">{timestamp_str}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Check for error state (T10)
                    if msg.get("error_type"):
                        st.markdown(
                            f'<div class="error-card">'
                            f'<strong>⚠️ {msg["error_type"].replace("_", " ").title()}</strong><br>'
                            f'{msg.get("error_message", "An error occurred.")}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        continue

                    answer_html = msg["content"].replace("\n", "<br>")
                    answer_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', answer_html)
                    answer_html = re.sub(r'`([^`]+)`', r'<code>\1</code>', answer_html)

                    is_fallback = msg.get("is_fallback", False)
                    fallback_html = ""
                    if is_fallback:
                        fallback_html = '<div class="fallback-label">⚠️ Based on general knowledge — not verified against course materials</div>'

                    # Source chips with ChromaDB metadata (T10)
                    sources_html = ""
                    if msg.get("source_references"):
                        sources_html = '<div class="source-label">📄 Retrieved from:</div>'
                        for src in msg["source_references"]:
                            filename = src.get("filename") or src.get("source_file") or src.get("source") or "Document"
                            page_number = src.get("page_number") or src.get("page") or "?"
                            section = src.get("section") or src.get("topic") or ""
                            section_str = f" · {section}" if section else ""
                            collection = src.get("collection_name", "")
                            collection_str = f" [{collection}]" if collection else ""
                            sim_pct = int(src.get("similarity", 0) * 100)
                            sources_html += (
                                f'<span class="source-chip">'
                                f'📄 {filename} · p.{page_number}'
                                f'{section_str} · {sim_pct}%{collection_str}'
                                f'</span>'
                            )

                    confidence = _confidence_score(msg.get("confidence"), msg.get("confidence_score"))
                    conf_color = "#10B981" if confidence > 0.8 else ("#D4A843" if confidence > 0.5 else "#EF4444")
                    conf_pct = int(confidence * 100)
                    conf_label = get_confidence_label(msg.get("confidence", confidence))
                    model_used = msg.get("model_used", "")
                    model_badge = get_model_badge(model_used)
                    msg_class = "ai-msg-fallback" if is_fallback else "ai-msg"
                    api_indicator = " · 🟢 Live API" if msg.get("from_api") else ""

                    st.markdown(f"""
                    <div class="clearfix"><div class="{msg_class}">
                        {fallback_html}
                        {answer_html}
                        {sources_html}
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {conf_pct}%; background: {conf_color};"></div>
                        </div>
                        <div class="confidence-text">
                            {conf_label}: {conf_pct}% · {model_badge} · {timestamp_str}{api_indicator}
                        </div>
                    </div></div>
                    """, unsafe_allow_html=True)

                    # Retrieval details expander (T10)
                    rmeta = msg.get("retrieval_metadata")
                    if rmeta:
                        with st.expander("🔍 Retrieval Details"):
                            rc1, rc2, rc3, rc4 = st.columns(4)
                            rc1.metric("Chunks Retrieved", rmeta.get("num_chunks_retrieved", "—"))
                            rc2.metric("Above Threshold", rmeta.get("num_chunks_above_threshold", "—"))
                            rc3.metric("Retrieval Time", f"{rmeta.get('retrieval_time_ms', '—')} ms")
                            rc4.metric("Generation Time", f"{rmeta.get('generation_time_ms', '—')} ms")

                            st.markdown(
                                f"**Embedding Model:** `{rmeta.get('embedding_model', '—')}` "
                                f"({rmeta.get('embedding_dimensions', '—')}-dim) · "
                                f"**Vector DB:** `{rmeta.get('vector_db', '—')}` · "
                                f"**Metric:** {rmeta.get('similarity_metric', '—')} · "
                                f"**Threshold:** {rmeta.get('similarity_threshold', '—')}"
                            )

            # Follow-up suggestions
            st.markdown("<br>", unsafe_allow_html=True)
            prompts = get_suggested_prompts()
            cols = st.columns(len(prompts))
            for i, prompt in enumerate(prompts):
                with cols[i]:
                    if st.button(f"💡 {prompt}", key=f"followup_{i}", use_container_width=True):
                        _send_message(prompt)
                        st.rerun()

    # ── Input bar ──
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
        # Show query state animation (T11)
        state_placeholder = st.empty()
        stages = [
            "🔍 Embedding your question...",
            "📚 Searching course documents...",
            "🧠 Generating response...",
        ]
        for stage in stages:
            state_placeholder.markdown(
                f'<div class="query-state"><div class="dot"></div> {stage}</div>',
                unsafe_allow_html=True,
            )
            time.sleep(0.3)

        _send_message(user_input.strip())
        state_placeholder.empty()
        st.rerun()


# ─── SESSION HISTORY PAGE ──────────────────────────────────────────

def render_history_page():
    st.markdown("### 📋 Session History")

    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        st.selectbox("Course", ["All courses", "CSIT321", "CSIT214", "ISIT312"], label_visibility="collapsed")
    with col2:
        st.selectbox("Period", ["Last 7 days", "Last 30 days", "All time"], label_visibility="collapsed")
    with col3:
        st.text_input("Search", placeholder="🔍 Search conversations...", label_visibility="collapsed")

    st.divider()

    # Combine real sessions with demo data
    real_sessions = st.session_state.get("sessions", [])
    demo_sessions = [
        {"session_id": "demo-1", "title": "RAG Pipeline Deep Dive", "course_id": "CSIT321", "created_at": "Today, 2:30 PM", "message_count": 8, "messages": [None]*8, "preview": "Asked about retrieval steps, embedding dimensions, and chunk overlap strategies..."},
        {"session_id": "demo-2", "title": "Database Normalization", "course_id": "CSIT214", "created_at": "Today, 10:15 AM", "message_count": 5, "messages": [None]*5, "preview": "Explored 1NF through 3NF with examples, discussed denormalization trade-offs..."},
        {"session_id": "demo-3", "title": "SQL Joins Overview", "course_id": "CSIT214", "created_at": "Yesterday, 4:45 PM", "message_count": 12, "messages": [None]*12, "preview": "Covered INNER, LEFT, RIGHT, FULL joins with visual diagrams and practice queries..."},
        {"session_id": "demo-4", "title": "Week 5 Lecture Summary", "course_id": "CSIT214", "created_at": "Yesterday, 11:00 AM", "message_count": 3, "messages": [None]*3, "preview": "Quick summary of indexing concepts, B-trees, and hash indexes from Week 5..."},
    ]
    all_sessions = real_sessions + demo_sessions
    accent_colors = ["#0D9488", "#1B2A4A", "#D4A843", "#0D9488", "#64748B"]

    for i, session in enumerate(all_sessions[:8]):
        title = session.get("title", "Untitled")
        course = session.get("course_id", "CSIT214")
        created = session.get("created_at", "—")
        msg_count = session.get("message_count", len(session.get("messages", [])))
        preview = session.get("preview", f"{msg_count} messages in this session")
        color = accent_colors[i % len(accent_colors)]

        st.markdown(f"""
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px 24px; margin: 8px 0;
                    border-left: 4px solid {color}; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-weight: 600; font-size: 1rem; color: #1E293B;">{title}</span>
                    <span class="status-badge badge-ready" style="margin-left: 10px;">{course}</span>
                </div>
                <span style="color: #64748B; font-size: 0.82rem;">{created}</span>
            </div>
            <p style="color: #475569; font-size: 0.88rem; margin: 8px 0;">{preview}</p>
            <div style="display: flex; gap: 24px; align-items: center;">
                <span style="color: #64748B; font-size: 0.8rem;">💬 {msg_count} messages</span>
                <span style="color: #64748B; font-size: 0.8rem;">📄 sources cited</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns([6, 1, 1])
        with c2:
            if st.button("Continue", key=f"continue_{i}"):
                if session["session_id"].startswith("demo-"):
                    pass  # Demo sessions can't be resumed
                else:
                    switch_session(session["session_id"])
                st.session_state.current_page = "chat"
                st.rerun()
        with c3:
            st.button("Delete", key=f"delete_{i}", type="secondary")


# ─── UPLOADS PAGE (Student view) ──────────────────────────────────

def render_uploads_page():
    st.markdown("### 📁 My Uploads")

    uploaded_files = st.file_uploader(
        "Upload course materials",
        type=["pdf", "pptx", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Drag and drop PDF, PPTX, DOCX, TXT, or MD files here",
    )

    # Upload progress simulation (T11)
    if uploaded_files:
        for f in uploaded_files:
            _simulate_upload_progress(f.name, len(f.getvalue()))

    st.divider()
    st.markdown("**Uploaded Documents**")
    _render_document_table(student_view=True)


# ─── DOCUMENT MANAGER (Lecturer / Admin view) ──────────────────────

def render_doc_manager_page():
    st.markdown("### 📁 Document Manager")
    role = st.session_state.user.get("role", "Student")
    st.markdown(f"<span class='status-badge badge-processing'>{role} View</span>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload course materials",
        type=["pdf", "pptx", "docx", "txt", "md"],
        accept_multiple_files=True,
        help="Drag and drop PDF, PPTX, DOCX, TXT, or MD files here. Max 50 MB per file.",
    )

    # Upload progress simulation (T11)
    if uploaded_files:
        for f in uploaded_files:
            _simulate_upload_progress(f.name, len(f.getvalue()))

    col1, col2, col3 = st.columns([3, 3, 2])
    with col1:
        st.selectbox("Course", ["CSIT321 - Project Development", "CSIT214 - Database Systems", "ISIT312 - Big Data"], label_visibility="collapsed")
    with col3:
        if st.button("🔄 Refresh Status", type="primary", use_container_width=True):
            st.info("Document statuses refreshed.")

    st.divider()
    st.markdown("**UPLOADED DOCUMENTS**")
    _render_document_table(student_view=False)


def _simulate_upload_progress(filename: str, file_size: int):
    """Show staged upload progress (T11)."""
    progress_placeholder = st.empty()
    stages = [
        ("⬆️ Uploading", "upload"),
        ("📝 Extracting text", "extract"),
        ("✂️ Chunking (~500 tokens)", "chunk"),
        ("🧬 Embedding (all-MiniLM-L6-v2)", "embed"),
        ("💾 Indexing in ChromaDB", "index"),
        ("✅ Complete", "done"),
    ]

    for step_idx, (label, _) in enumerate(stages):
        html = f'<div class="upload-progress"><strong>{filename}</strong> ({file_size / 1024:.1f} KB)<br>'
        for j, (slabel, _) in enumerate(stages):
            if j < step_idx:
                html += f'<div class="upload-step upload-step-done">✅ {slabel}</div>'
            elif j == step_idx:
                html += f'<div class="upload-step upload-step-active">⏳ {slabel}...</div>'
            else:
                html += f'<div class="upload-step upload-step-pending">⬜ {slabel}</div>'
        html += '</div>'
        progress_placeholder.markdown(html, unsafe_allow_html=True)
        time.sleep(0.4)

    time.sleep(0.3)
    progress_placeholder.success(f"✅ {filename} — uploaded and indexed successfully!")


def _render_document_table(student_view: bool = False):
    """Render document list with status badges (shared by uploads + doc manager)."""
    docs_data = [
        {"name": "Week3_Lecture_Normalisation.pdf", "type": "PDF", "size": "2.4 MB", "status": "Indexed", "uploaded": "15 Apr 2026", "chunks": 24},
        {"name": "DatabaseNotes_Joins_Indexing.pptx", "type": "PPTX", "size": "5.1 MB", "status": "Indexed", "uploaded": "15 Apr 2026", "chunks": 18},
        {"name": "Textbook_Ch9_QueryOptimisation.pdf", "type": "PDF", "size": "8.7 MB", "status": "Indexed", "uploaded": "14 Apr 2026", "chunks": 38},
    ]
    if not student_view:
        docs_data += [
            {"name": "Week5_Indexing_QueryPlans.docx", "type": "DOCX", "size": "1.1 MB", "status": "Processing", "uploaded": "20 Apr 2026", "chunks": 0},
            {"name": "RAG_Pipeline_Overview.pdf", "type": "PDF", "size": "1.8 MB", "status": "Indexed", "uploaded": "13 Apr 2026", "chunks": 16},
        ]

    headers = ["File Name", "Type", "Size", "Status", "Uploaded"]
    if not student_view:
        headers.append("Actions")
    cols = st.columns([4, 1, 1, 1, 2] + ([1] if not student_view else []))
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    for doc in docs_data:
        cols = st.columns([4, 1, 1, 1, 2] + ([1] if not student_view else []))
        cols[0].markdown(f"📄 {doc['name']}")
        cols[1].markdown(f"<span style='color: #475569;'>{doc['type']}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span style='color: #475569;'>{doc['size']}</span>", unsafe_allow_html=True)
        badge_class = "badge-indexed" if doc["status"] == "Indexed" else ("badge-processing" if doc["status"] == "Processing" else "badge-failed")
        cols[3].markdown(f"<span class='status-badge {badge_class}'>{doc['status']}</span>", unsafe_allow_html=True)
        cols[4].markdown(f"<span style='color: #475569;'>{doc['uploaded']}</span>", unsafe_allow_html=True)
        if not student_view:
            c1, c2 = cols[5].columns(2)
            c1.button("🔄", key=f"retry_{doc['name']}")
            c2.button("🗑️", key=f"delmgr_{doc['name']}")

    st.divider()
    indexed = sum(1 for d in docs_data if d["status"] == "Indexed")
    total_chunks = sum(d.get("chunks", 0) for d in docs_data)
    st.caption(f"{len(docs_data)} documents · {indexed} indexed · {total_chunks} chunks · Semantic search ON")


# ─── ADMIN DASHBOARD (Admin only) ──────────────────────────────────

def render_admin_page():
    st.markdown("### ⚙️ Admin Dashboard")
    st.markdown("<span class='status-badge' style='background:#FEE2E2; color:#991B1B;'>Admin</span>", unsafe_allow_html=True)

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
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    for u in users:
        cols = st.columns([3, 2, 2, 1, 1, 2])
        cols[0].markdown(f"**{u['name']}**<br><span style='color:#64748B; font-size:0.8rem;'>{u['email']}</span>", unsafe_allow_html=True)
        role_color = "#1B2A4A" if u["role"] == "Admin" else ("#0D9488" if u["role"] == "Lecturer" else "#64748B")
        cols[1].markdown(f"<span class='status-badge' style='background:{role_color}20; color:{role_color};'>{u['role']}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span style='color: #475569;'>{u['last']}</span>", unsafe_allow_html=True)
        cols[3].markdown(f"<span style='color: #475569;'>{u['queries']}</span>", unsafe_allow_html=True)
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
        st.selectbox("Chunk", ["~500 tokens / 50 overlap", "~256 tokens / 25 overlap", "~1024 tokens / 100 overlap"], label_visibility="collapsed", key="chunk_size")

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
        st.session_state.current_page = "chat"
        st.rerun()


if __name__ == "__main__":
    main()
