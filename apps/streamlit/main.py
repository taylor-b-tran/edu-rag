"""
Paedia — AI-Powered Course Assistant
Streamlit UI Prototype — wired to Flask API via api_client.py
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)

Sprint 5 updates:
  S5-T09: Fixed readability/contrast — all text visible, buttons readable
  S5-T10: Connected query flow to backend evidence — ChromaDB metadata, model info, error states
  S5-T11: Improved upload + history flow — timestamps, query state, session management

Sprint 6 updates:
  T05: Multi-subject selector — sidebar course dropdown, "My Courses" card page,
       course-scoped chat header. All backed by real /api/courses endpoints.

Sprint 8 updates:
  T8-05: Student course enrollment — My Courses page now shows available courses
         with a Join button that calls POST /api/courses/<code>/join.
  T8-06: Signup UI — tabbed Sign In / Sign Up on login page, POST /api/auth/signup,
         auto-login on success, inline validation and API error display.
  T8-07: Removed hardcoded content — suggested prompts are now course-aware and
         built from indexed documents, UOW-specific placeholders replaced.
  T8-11: Response-style picker — dropdown in chat header fetches styles from
         GET /api/response-styles and passes selection to POST /api/query.

Sprint 9 updates:
  T9-13: Session history — Delete button calls DELETE /api/sessions/<id>,
         Continue loads the correct session (not just the most recent).
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import logging
import os
import html as _html
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from functools import lru_cache

from api_client import PaediaAPIClient, APIConfig, APIReadError


@lru_cache(maxsize=None)
def _display_zone(name):
    """Resolve each configured zone once and warn once if it cannot be used."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logging.getLogger(__name__).warning("Invalid PAEDIA_TIMEZONE %r; using Australia/Sydney.", name)
        return ZoneInfo("Australia/Sydney")


def _local(ts):
    """Convert server timestamps (naive values are UTC) to the display zone.

    PAEDIA_TIMEZONE overrides Australia/Sydney; zoneinfo handles daylight saving.
    Missing or malformed legacy timestamps remain unknown.
    """
    if not ts:
        return None
    try:
        value = ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_display_zone(os.environ.get("PAEDIA_TIMEZONE", "Australia/Sydney").strip()))

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

/* ── Force light-theme CSS custom properties (prevents dark mode override) ── */
:root,
html[data-theme="dark"],
html[data-theme="light"],
html {
    --primary-color: #0D9488 !important;
    --background-color: #F8F9FA !important;
    --secondary-background-color: #FFFFFF !important;
    --text-color: #1E293B !important;
    --font: 'Inter', sans-serif !important;
    color-scheme: light !important;
}

html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.stApp {
    background-color: #F8F9FA !important;
    color: #1E293B !important;
    color-scheme: light !important;
}

/* ── Universal text visibility — nuclear option for dark-mode resistance ── */
.stApp .main .block-container,
.stApp .main .block-container * {
    color: #1E293B;
}

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
div[data-baseweb="select"] * {
    color: #1B2A4A !important;
}
div[data-baseweb="popover"] * {
    color: #1B2A4A !important;
    background-color: #FFFFFF !important;
}
div[role="listbox"] * {
    background-color: #FFFFFF !important;
    color: #1B2A4A !important;
}

/* ── Tabs, Expanders, Alerts — readability ── */
.stTabs [data-baseweb="tab-list"] button {
    color: #475569 !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #0D9488 !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span {
    color: #1E293B !important;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    color: #1E293B !important;
}
.stAlert p, .stAlert span, .stAlert div {
    color: inherit !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748B !important;
}

/* ── File uploader area ── */
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p {
    color: #334155 !important;
}
[data-testid="stFileUploader"] section {
    border-color: #CBD5E1 !important;
    background-color: #FFFFFF !important;
}

/* ── Dividers ── */
.stApp hr,
.stApp [data-testid="stMain"] hr {
    border-color: #E2E8F0 !important;
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
.user-msg .msg-time { color: rgba(255,255,255,0.85); font-size: 0.72rem; margin-top: 6px; }

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
.ai-msg .msg-time { color: #64748B; font-size: 0.72rem; margin-top: 6px; }

.ai-msg-fallback {
    background: #FFFBEB; color: #1E293B;
    padding: 18px 22px; border-radius: 18px 18px 18px 4px;
    margin: 8px 0; max-width: 85%; float: left; clear: both;
    font-size: 0.95rem; line-height: 1.6;
    border: 2px solid #D4A843;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.ai-msg-fallback .msg-time { color: #64748B; font-size: 0.72rem; margin-top: 6px; }

.fallback-label {
    display: flex; width: fit-content; align-items: center; gap: 6px;
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

/* ── Source chips — labels, not links ── */
.source-chip {
    display: inline-block; background: #F1F5F9; border: 1px solid #E2E8F0;
    border-radius: 16px; padding: 5px 14px; margin: 4px 6px 4px 0;
    font-size: 0.8rem; color: #475569;
}
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
.status-badge { display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; white-space: nowrap; }
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
    border-radius: 8px; padding: 8px 12px; margin: 4px 0; color: #CBD5E1;
}
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
/* A long file name ends in an ellipsis; the full name is in the title attribute. */
.doc-card-name {
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    font-size: 0.82rem; color: #CBD5E1;
}

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
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "sample_responses.json")
    if os.path.exists(fixture_path):
        with open(fixture_path, "r") as f:
            return json.load(f)
    alt_path = os.path.join("fixtures", "sample_responses.json")
    if os.path.exists(alt_path):
        with open(alt_path, "r") as f:
            return json.load(f)
    return None


data = load_responses() if APIConfig().use_fixtures else None


# ─── API CLIENT ───────────────────────────────────────────────────

# One client per browser session -- deliberately not @st.cache_resource.
#
# st.cache_resource hands the same object to every session the server is
# running, and PaediaAPIClient keeps the signed-in user's JWT on the instance.
# So one cached client meant one token shared by everybody: whoever logged in
# most recently owned every other tab's requests, and a single sign-out
# revoked the lot. Nothing about it looks wrong on screen, and it cannot show
# up at all while testing happens one browser at a time -- which is how it
# went unnoticed for so long.
#
# session_state is per browser session, which is the scope a credential
# belongs in.
_API_CLIENT_KEY = "_api_client"


def get_api_client() -> PaediaAPIClient:
    client = st.session_state.get(_API_CLIENT_KEY)
    if client is None:
        client = PaediaAPIClient(APIConfig())
        st.session_state[_API_CLIENT_KEY] = client
    return client


class _SessionAPIClient:
    """Resolves `api.<attr>` to the calling session's client, at call time.

    Binding `api = get_api_client()` once at module level would reintroduce
    the bug in a quieter form: module globals are shared by every ScriptRunner
    thread, so two sessions rerunning at the same time overwrite each other's
    binding and one can finish its run holding the other's client. Doing the
    lookup on each attribute access keeps it inside the session that asked.
    """

    def __getattr__(self, name):
        return getattr(get_api_client(), name)


api = _SessionAPIClient()
# Live selectors are populated from authorized course data, never seeded codes.
COURSE_FALLBACKS = []
LOGIN_COMPONENT_DIR = os.path.join(os.path.dirname(__file__), "components", "login_form")
login_form_component = components.declare_component("paedia_login_form", path=LOGIN_COMPONENT_DIR)


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
    ui_user["name"] = ui_user.get("name") or ui_user.get("username") or ui_user.get("email") or "User"
    return ui_user


def _all_courses() -> list[dict]:
    """Courses from the selected live or explicit demo data source."""
    return api.get_courses()


def _course_options_for_user(user: dict) -> list[str]:
    """An empty successful result is empty; failed reads raise APIReadError."""
    all_courses = _all_courses()
    enrolled = set(user.get("enrolled_courses", []) or [])
    role = str(user.get("role", "")).lower()
    options: list[str] = []
    for course in all_courses:
        code = course.get("course_code")
        if not code or not course.get("is_active", True):
            continue
        if role == "admin" or code in enrolled:
            options.append(code)
    return list(dict.fromkeys(options))


# Apply the preferred course only within the user's available options.
_PREFERRED_COURSE = "CSIT321"


def _preferred_from(options: list[str]) -> str:
    """Pick from courses the user may open, or "" when there are none."""
    if not options:
        return ""
    return _PREFERRED_COURSE if _PREFERRED_COURSE in options else options[0]


def _default_course_for_user(user: dict) -> str:
    """The course to open on, or "" when the user is in none."""
    return _preferred_from(_course_options_for_user(user))


def _active_course() -> str:
    """Choose an available course, refreshing options for an uncached selection."""
    current = st.session_state.get("course_id") or ""
    # Cached selections avoid a courses request on each rerun. A new selection
    # may refer to a course created or reactivated since login.
    options = st.session_state.get("course_options") or []
    if not options or (current and current not in options):
        try:
            options = _course_options_for_user(st.session_state.get("user") or {})
            st.session_state.course_options = options
        except Exception:
            # Preserve the selection on a failed read. Authorization remains
            # enforced by the API for each operation.
            return current
    if current and current in options:
        return current
    return _preferred_from(options)


def _reconcile_active_course() -> str:
    """Synchronize page and picker state before the sidebar and page render."""
    resolved = _active_course()
    if resolved != (st.session_state.get("course_id") or ""):
        st.session_state.course_id = resolved
        st.session_state.selected_course_id = resolved
    return resolved


def _course_display_label(course_code: str) -> str:
    for course in _all_courses():
        if course.get("course_code") == course_code:
            name = course.get("name")
            return f"{course_code} — {name}" if name else course_code
    return course_code


def _refresh_course_options() -> None:
    """Call after an admin creates/deactivates a course so the current
    session's selector picks it up without needing to log out and back in."""
    user = st.session_state.get("user")
    if not user:
        return
    st.session_state.course_options = _course_options_for_user(user)


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
        "course_id": "",
        "course_options": COURSE_FALLBACKS,
        "selected_course_id": "",
        "login_error": None,
        "signup_error": None,
        "last_login_nonce": None,
        "pending_send": False,
        "query_state": None,
        "upload_progress": None,
        "response_style": None,
        "response_styles_cache": None,
        "history_load_pending": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ─── HELPER: SESSION MANAGEMENT (T11) ─────────────────────────────

def _hydrate_sessions_from_server() -> None:
    """Load this user's saved conversations back into the UI (T9-14).

    Conversations have been persisted in Postgres since T8-24, and readable
    from any gunicorn worker since PR #90 -- but nothing ever read them back
    for the person who owned them. The sidebar and Session History both render
    `st.session_state.sessions`, which only holds conversations created in the
    current browser tab. Close the tab and your history looked deleted while
    every message was still on disk; 103 sessions were sitting there unread.

    Failed reads stay visible and are retried on the next run.
    """
    st.session_state.history_load_pending = True
    remote = api.get_sessions()
    st.session_state.history_load_pending = False
    restored = []
    for item in sorted(remote, key=lambda s: s.get("updated_at") or "", reverse=False):
        if item.get("archived"):
            continue
        sid = item.get("session_id")
        turns = item.get("messages") or []
        if not sid or not turns:
            continue

        messages = []
        for turn in turns:
            stamp = turn.get("created_at") or ""
            local_stamp = _local(stamp)
            display_time = local_stamp.strftime("%I:%M %p") if local_stamp else ""
            messages.append({"role": "user", "content": turn.get("question", ""),
                             "timestamp": display_time, "timestamp_full": stamp})
            messages.append({"role": "assistant", "content": turn.get("answer", ""),
                             "source_references": turn.get("sources") or [],
                             **{key: value for key, value in (turn.get("response_metadata") or {}).items()
                                if key in ("confidence", "confidence_score", "model_used", "latency_ms",
                                           "is_fallback", "backend_mode", "retrieval_metadata",
                                           "token_count", "response_style")},
                             "from_api": True,
                             "timestamp": display_time, "timestamp_full": stamp})

        first = turns[0].get("question") or "Chat"
        restored.append({
            "session_id": sid,
            "backend_session_id": sid,
            "title": first[:40] + ("..." if len(first) > 40 else ""),
            "messages": messages,
            # "" rather than a default: switch_session below reads it back
            # the same way, and _active_course resolves it per screen.
            "course_id": item.get("course_id") or "",
            "created_at": _local(item["created_at"]).strftime("%Y-%m-%d %H:%M") if _local(item.get("created_at")) else "",
            "message_count": len(messages),
        })

    st.session_state.sessions = restored
    # The URL is a per-tab selection hint, never an authorization credential.
    # Only IDs returned by the authenticated, owner-filtered history may open.
    requested = st.query_params.get("chat")
    for session in restored:
        if session["backend_session_id"] == requested and session["course_id"] in st.session_state.course_options:
            switch_session(session["session_id"])
            return
    course = st.query_params.get("course")
    if course in st.session_state.course_options:
        st.session_state.course_id = course
    create_new_session("Welcome Chat")


def _remember_chat_selection() -> None:
    """Persist only the active backend ID and course in this tab's URL."""
    params = st.query_params.to_dict()
    sid = st.session_state.get("session_id")
    if sid:
        params["chat"] = sid
    else:
        params.pop("chat", None)
    params["course"] = st.session_state.get("course_id") or ""
    st.query_params.from_dict(params)


def _change_chat_course() -> None:
    chosen = st.session_state.selected_course_id
    # A rerun the picker did not cause can still deliver the picker's value,
    # and that value can be empty. Naming no course is not a request to change
    # course; treating it as one moves the chat to whichever course the
    # resolution rule falls back to.
    if not chosen or chosen == st.session_state.course_id:
        return
    st.session_state.course_id = chosen
    create_new_session()


def create_new_session(title="New Chat", *, course_transition=False):
    """Create a new chat session and make it active."""
    course_id = st.session_state.get("course_id") or ""
    session = {
        "session_id": str(uuid.uuid4())[:8],
        "backend_session_id": None,
        "title": title,
        "messages": [],
        "course_id": course_id,
        "created_at": _local(datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M"),
        "message_count": 0,
        "course_transition_notice": course_transition,
    }
    st.session_state.sessions.append(session)
    st.session_state.active_session_id = session["session_id"]
    st.session_state.session_id = None
    st.session_state.course_id = course_id
    st.session_state.selected_course_id = course_id
    st.session_state.messages = session["messages"]
    _remember_chat_selection()
    return session


def get_active_session():
    """Return the active session, creating one if needed."""
    if not st.session_state.sessions:
        return create_new_session()
    for s in st.session_state.sessions:
        if s["session_id"] == st.session_state.active_session_id:
            return s
    session = st.session_state.sessions[-1]
    switch_session(session["session_id"])
    return session


def switch_session(session_id):
    """Switch to a different chat session."""
    for s in st.session_state.sessions:
        if s["session_id"] == session_id:
            st.session_state.active_session_id = session_id
            st.session_state.messages = s["messages"]
            st.session_state.session_id = s.get("backend_session_id")
            st.session_state.course_id = s.get("course_id") or ""
            st.session_state.selected_course_id = st.session_state.course_id
            _remember_chat_selection()
            return


# ─── RAG QUERY ─────────────────────────────────────────────────────

def get_ai_response(query: str) -> dict:
    """Query the RAG pipeline via the API client."""
    course_id = _active_course()
    session_id = st.session_state.get("session_id")
    style = st.session_state.get("response_style")
    return api.query(query, course_id=course_id, session_id=session_id,
                     response_style=style)


def get_suggested_prompts() -> list:
    """Return context-aware prompt suggestions based on the active course.

    T8-07: replaced the six hardcoded strings from fixtures with prompts
    that reference the user's selected course and its indexed documents.
    Cached per course so the buttons don't reshuffle on every re-run.
    """
    course_id = _active_course()

    # Return cached prompts if the course hasn't changed
    cached = st.session_state.get("_cached_prompts_course")
    if cached == course_id and st.session_state.get("_cached_prompts"):
        return st.session_state["_cached_prompts"]

    docs = api.get_documents(course_id)
    # Only a document that holds chunks can actually be summarised. Naming the
    # first row regardless put "Summarise RAG_Pipeline_Overview" on the landing
    # screen for a document with no chunks anywhere in the vector store, so the
    # answer came from unrelated material and nothing said so.
    docs = [d for d in docs if (d.get("chunks") or 0) > 0]
    # Use original_filename (T8-28: uploads store under a generated name)
    doc_names = [
        (d.get("original_filename") or d.get("filename") or d.get("name") or "")
        for d in docs
    ]
    doc_names = [n for n in doc_names if n]

    prompts: list[str] = []
    if doc_names:
        first_doc = doc_names[0].rsplit(".", 1)[0]
        prompts.append(f"Summarise {first_doc}")
    prompts.append(f"What topics are covered in {course_id}?")
    prompts.append(f"Give me a quick quiz on {course_id}")
    prompts.append(f"Explain the key concepts from the latest lecture")
    if len(doc_names) > 1:
        second_doc = doc_names[1].rsplit(".", 1)[0]
        prompts.append(f"Compare themes in {first_doc} and {second_doc}")
    prompts.append(f"What should I revise for {course_id}?")

    # T8-07: these used to be random.sample(). Streamlit re-runs the whole
    # script on every interaction, so a reshuffled list meant the button a
    # student clicked was not necessarily the question that got submitted --
    # the label came from the previous run, the action from the current one.
    # The order these were appended in is already most-specific-first, so
    # taking the first four is both stable and the better selection.
    picked = prompts[:4]
    st.session_state["_cached_prompts_course"] = course_id
    st.session_state["_cached_prompts"] = picked
    return picked


def get_model_badge(model_used: str) -> str:
    """Return HTML badge for the LLM model used (T10)."""
    model_used = _html.escape(str(model_used or "unknown"))
    if "ollama" in model_used.lower():
        return f'<span class="model-badge model-ollama">🦙 {model_used}</span>'
    elif "openai" in model_used.lower() or "gpt" in model_used.lower():
        return f'<span class="model-badge model-openai">🤖 {model_used}</span>'
    return f'<span class="model-badge model-unknown">🔧 {model_used}</span>'


# The pipeline decides the confidence band and returns it with every answer
# (CONFIDENCE_HIGH / CONFIDENCE_MEDIUM in src/document_processor/rag_pipeline.py).
# These copies exist only for messages that carry a bare score, and a test keeps them
# equal to the pipeline's: when the two scales differed, a 0.64 answer was labelled
# "High confidence" by the pipeline and painted gold by this page.
_CONFIDENCE_HIGH = 0.60
_CONFIDENCE_MEDIUM = 0.35
_BAND_COLOURS = {"High": "#10B981", "Medium": "#D4A843", "Low": "#EF4444"}


def _confidence_score(confidence, confidence_score=None) -> float:
    if isinstance(confidence_score, (int, float)):
        return max(0.0, min(float(confidence_score), 1.0))
    if isinstance(confidence, (int, float)):
        return max(0.0, min(float(confidence), 1.0))
    if isinstance(confidence, str):
        # Mid-band widths, so a bar drawn from a label alone sits inside its own band.
        label_scores = {"high": 0.8, "medium": 0.5, "low": 0.2}
        lowered = confidence.lower()
        if lowered in label_scores:
            return label_scores[lowered]
        try:
            return max(0.0, min(float(confidence), 1.0))
        except ValueError:
            return 0.0
    return 0.0


def _confidence_band(confidence, confidence_score=None):
    """The band the pipeline assigned, or the same band derived from a bare score."""
    if isinstance(confidence, str) and confidence.strip().lower() in {"high", "medium", "low"}:
        return confidence.strip().capitalize()
    if confidence is None and confidence_score is None:
        return None
    score = _confidence_score(confidence, confidence_score)
    if score >= _CONFIDENCE_HIGH:
        return "High"
    if score >= _CONFIDENCE_MEDIUM:
        return "Medium"
    if score > 0:
        return "Low"
    return None


def get_confidence_label(confidence) -> str:
    """Return human-readable confidence label."""
    band = _confidence_band(confidence)
    return f"{band} confidence" if band else "No confidence data"


_FLASH_KEY = "_flash_messages"
_FLASH_LEVELS = ("success", "info", "warning", "error")
# How long a queued message stays eligible to be drawn. st.rerun() starts a new run, and
# Streamlit then often starts one or two more (the cookie component re-reports its
# value), so a message that is removed when it is first drawn is gone before it can be
# read. Drawn messages stay in the page until the next run replaces it, so a short
# lifetime is enough: the next click after this time clears it.
_FLASH_SECONDS = 15


def _flash(text, level="success", slot="page"):
    """Show `text` on the next run(s). Use it for any message that is followed by
    st.rerun(): an alert drawn in the run that reruns is gone before it can be read.
    The message belongs to the page it was queued on, and to `slot` within it."""
    pending = dict(st.session_state.get(_FLASH_KEY) or {})
    pending.setdefault(slot, []).append((
        level if level in _FLASH_LEVELS else "info", str(text),
        time.time(), st.session_state.get("current_page")))
    st.session_state[_FLASH_KEY] = pending


def _live_flashes(slot):
    now = time.time()
    page = st.session_state.get("current_page")
    return [(level, text) for level, text, stamp, queued_on
            in (st.session_state.get(_FLASH_KEY) or {}).get(slot, [])
            if now - stamp < _FLASH_SECONDS and queued_on == page]


def _show_flashes(slot="page"):
    """Draw the messages queued for `slot` on this page that have not expired."""
    for level, text in _live_flashes(slot):
        getattr(st, level)(text)


def _forget_flashes() -> None:
    """Call at the end of a run that completed: drop what has expired, and what
    belongs to a page the reader has left."""
    now = time.time()
    page = st.session_state.get("current_page")
    kept = {}
    for slot, items in (st.session_state.get(_FLASH_KEY) or {}).items():
        fresh = [i for i in items if now - i[2] < _FLASH_SECONDS and i[3] == page]
        if fresh:
            kept[slot] = fresh
    if kept:
        st.session_state[_FLASH_KEY] = kept
    else:
        st.session_state.pop(_FLASH_KEY, None)


def _clear_identity_state() -> None:
    """Drop the previous account's private UI data before reauthentication."""
    for key in ("authenticated", "jwt_token", "user", "messages", "sessions",
                "active_session_id", "session_id", "course_id", "course_options",
                "selected_course_id", "pending_send", "query_state", "current_page",
                "history_load_pending", "_cached_prompts", "_cached_prompts_course",
                "confirm_user_decision", "signup_notice", _FLASH_KEY):
        st.session_state.pop(key, None)
    init_session_state()


def handle_login_submit() -> None:
    """Authenticate from login form state."""
    email = st.session_state.get("login_email", "").strip()
    password = st.session_state.get("login_password", "")
    login_result = api.login(email, password)
    if login_result.get("success"):
        _clear_identity_state()
        user = _normalise_user_for_ui(login_result.get("user", {}))
        st.session_state.jwt_token = login_result.get("jwt_token")
        _remember_session(st.session_state.jwt_token)
        st.session_state.user = user
        st.session_state.course_options = _course_options_for_user(user)
        st.session_state.course_id = _default_course_for_user(user)
        st.session_state.selected_course_id = st.session_state.course_id
        st.session_state.authenticated = True
        st.session_state.login_error = None
        _hydrate_sessions_from_server()
        if not st.session_state.sessions:
            create_new_session("Welcome Chat")
    elif login_result.get("use_demo_auth"):
        user = DEMO_USERS.get(email)
        if user and user["password"] == password:
            user = _normalise_user_for_ui({k: v for k, v in user.items() if k != "password"})
            user["enrolled_courses"] = [c["course_code"] for c in _all_courses() if c.get("course_code")]
            st.session_state.authenticated = True
            st.session_state.user = user
            st.session_state.course_options = _course_options_for_user(user)
            st.session_state.course_id = _default_course_for_user(user)
            st.session_state.selected_course_id = st.session_state.course_id
            st.session_state.login_error = None
            create_new_session("Welcome Chat")
        else:
            st.session_state.login_error = "Invalid email or password."
    else:
        st.session_state.login_error = login_result.get("error") or "Invalid email or password."


def handle_signup_submit() -> None:
    """Register a new user via POST /api/auth/signup, then auto-login on success."""
    email = st.session_state.get("signup_email", "").strip()
    username = st.session_state.get("signup_username", "").strip()
    password = st.session_state.get("signup_password", "")
    confirm = st.session_state.get("signup_confirm", "")
    role = st.session_state.get("signup_role", "student").lower()
    st.session_state.signup_notice = None

    if not email or not username or not password:
        st.session_state.signup_error = "All fields are required."
        return
    if password != confirm:
        st.session_state.signup_error = "Passwords do not match."
        return

    result = api.signup(email, username, password, role)
    if result.get("pending"):
        # The account exists, but a lecturer has no access until an
        # administrator approves it, so nobody is signed in. This is not an
        # error: it is shown as a notice, and the sign-in page will say the
        # same thing until the decision is made.
        st.session_state.signup_error = None
        st.session_state.signup_notice = result.get("error") or (
            "Your lecturer account has been created. "
            "An administrator must approve it before you can sign in.")
    elif result.get("success"):
        # Auto-login: the signup response already contains tokens + user
        _clear_identity_state()
        user = _normalise_user_for_ui(result.get("user", {}))
        st.session_state.jwt_token = result.get("jwt_token")
        _remember_session(st.session_state.jwt_token)
        st.session_state.user = user
        st.session_state.course_options = _course_options_for_user(user)
        st.session_state.course_id = _default_course_for_user(user)
        st.session_state.selected_course_id = st.session_state.course_id
        st.session_state.authenticated = True
        st.session_state.signup_error = None
        st.session_state.login_error = None
        create_new_session("Welcome Chat")
    else:
        # Show the API error message as-is (it's already user-facing)
        st.session_state.signup_error = result.get("error") or "Signup failed."


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

        # ── Toggle between Sign In and Sign Up ──
        tab_login, tab_signup = st.tabs(["Sign In", "Sign Up"])

        # ──────────── SIGN IN TAB ────────────
        with tab_login:
            login_payload = login_form_component(
                default_email=st.session_state.get("login_email", ""),
                key="login_form_component",
            )

            if st.session_state.login_error:
                st.error(st.session_state.login_error)

            if isinstance(login_payload, dict) and login_payload.get("submitted"):
                nonce = login_payload.get("nonce")
                if nonce != st.session_state.get("last_login_nonce"):
                    st.session_state.last_login_nonce = nonce
                    st.session_state.login_email = login_payload.get("email", "")
                    st.session_state.login_password = login_payload.get("password", "")
                    handle_login_submit()
                    st.rerun()

        # ──────────── SIGN UP TAB (T8-06) ────────────
        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                st.text_input("Email", placeholder="you@example.com",
                              key="signup_email")
                st.text_input("Username", placeholder="Choose a username",
                              key="signup_username")
                st.text_input("Password", type="password",
                              placeholder="At least 10 characters",
                              key="signup_password")
                st.text_input("Confirm Password", type="password",
                              placeholder="Re-enter password",
                              key="signup_confirm")
                st.selectbox("I am a", ["Student", "Lecturer"],
                             key="signup_role",
                             format_func=lambda x: x)

                submitted = st.form_submit_button("Create Account", type="primary",
                                                   use_container_width=True)
                if submitted:
                    handle_signup_submit()
                    if st.session_state.authenticated:
                        st.rerun()

            if st.session_state.get("signup_notice"):
                st.success(st.session_state.signup_notice)
            if st.session_state.get("signup_error"):
                st.error(st.session_state.signup_error)

            st.caption("Password must be at least 10 characters, not a common password, "
                       "and different from your email or username.")

        st.markdown("---")
        st.caption("CSIT321 Project 37 · Group 19 — Aletheia's Zetetes")


# ─── SIDEBAR (T09: readability + T11: session management) ─────────

# How many documents the sidebar lists before "Show all".
_SIDEBAR_DOCS_SHOWN = 5


def render_sidebar():
    role = st.session_state.user.get("role", "Student")

    with st.sidebar:
        st.markdown("# 📚 Paedia")
        st.caption("AI Course Assistant")
        st.divider()

        # Navigation buttons
        pages = {"chat": ("💬", "Q&A Chat"), "courses": ("📚", "My Courses"), "history": ("📋", "Session History")}
        if role in ("Lecturer", "Admin"):
            pages["doc_manager"] = ("📁", "Document Manager")
        else:
            pages["uploads"] = ("📚", "Course Materials")
        if role in ("Lecturer", "Admin"):
            pages["settings"] = ("⚙️", "Tuning")
        if role == "Admin":
            pages["admin"] = ("🛠️", "Admin Dashboard")

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
            title = _html.escape(s["title"][:30] + ("..." if len(s["title"]) > 30 else ""))
            msg_count = _saved_message_count(s.get("messages"))
            st.markdown(
                f"<div class='{card_class}'>"
                f"<div class='session-title'>💬 {title}</div>"
                f"<div class='session-meta'>{msg_count} msgs · {_html.escape(s.get('created_at', ''))}</div>"
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
        course_id = _active_course()
        docs = []
        if course_id:
            try:
                docs = api.get_documents(course_id)
            except APIReadError:
                st.warning("Course documents could not be loaded. You can still use My Courses or sign out.")
        else:
            st.caption(_no_course_hint(role))
        # Five by default, all of them on request. Only the first five used to
        # be listed while the line below reported the full count, so ten loaded
        # documents looked like five. The toggle resets when the course changes.
        if st.session_state.get("sidebar_docs_course") != course_id:
            st.session_state.sidebar_docs_course = course_id
            st.session_state.sidebar_docs_all = False
        if len(docs) <= _SIDEBAR_DOCS_SHOWN:
            # Nothing to expand, so a later, longer list starts collapsed.
            st.session_state.sidebar_docs_all = False
        show_all = bool(st.session_state.get("sidebar_docs_all"))
        for doc in (docs if show_all else docs[:_SIDEBAR_DOCS_SHOWN]):
            doc_name = _html.escape(doc.get("original_filename") or doc.get("filename") or doc.get("name") or "Unknown")
            status_color = _document_status_dot(doc)
            st.markdown(
                f"<div class='doc-card'>"
                f"<span>📄</span>"
                f"<span class='doc-card-name' title='{doc_name}'>{doc_name}</span>"
                f"<span style='flex:0 0 10px; width:10px; height:10px; border-radius:50%; background:{status_color}; display:inline-block;'></span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        # A button rather than st.expander: the expander's arrow depends on a
        # web font that does not load in every environment.
        if len(docs) > _SIDEBAR_DOCS_SHOWN:
            label = "Show fewer" if show_all else f"Show all {len(docs)}"
            if st.button(label, key="sidebar_docs_toggle", use_container_width=True):
                st.session_state.sidebar_docs_all = not show_all
                st.rerun()

        st.divider()
        docs_count = len(docs)
        # Counted through _document_status so the sidebar cannot say "7 indexed"
        # while the Document Manager shows one of them as holding no chunks.
        indexed = _document_indexed_count(docs)
        api_icon = "🟢" if api.is_live else "🟡"
        # T8-07: this line used to end with a flat "Semantic search ON", printed
        # whether or not it was. If the embedder fails to load the backend falls
        # back to keyword matching and answers get noticeably worse -- the one
        # moment the caption mattered was the one moment it lied. /api/health
        # reports what is actually loaded, so ask it.
        health = api.get_health()
        embedder_ok = (health.get("embedder") or {}).get("status") == "ok"
        if health.get("rag_available") and embedder_ok:
            search_label = "Semantic search on"
        elif health.get("_unavailable"):
            search_label = "Search state unknown"
        else:
            search_label = "⚠️ Semantic search unavailable"
        st.caption(f"{docs_count} docs loaded · {indexed} indexed · {search_label}")
        st.caption(f"{api_icon} {api.mode_label}")

        # ── User info + logout ──
        st.markdown("---")
        initials = _html.escape("".join(w[0] for w in st.session_state.user.get("name", "U").split()[:2]))
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
            if api.clear_auth():
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                _forget_session()
                st.rerun()
            else:
                st.error("Sign out could not be confirmed. Please try again.")


# ─── CHAT PAGE (T09+T10+T11: full overhaul) ───────────────────────

def _scroll_to_latest() -> None:
    """Scroll the chat to its end once the page has been drawn.

    Streamlit keeps a chat pinned to the bottom only while the reader is
    already there. A reader who had scrolled up to re-read an answer and then
    asked the next question stayed at the top, so the new question, the
    "Generating response..." line and the finished answer were all off screen
    and the page looked frozen. The scrolling element is found by the class
    `stMain`, which is on it whether or not it also carries the chat's own test
    id. If the parent page cannot be reached the script does nothing, which is
    the old behaviour.
    """
    nonce = st.session_state.get("_scroll_nonce", 0) + 1
    st.session_state["_scroll_nonce"] = nonce   # a new element each time, so the script runs again
    components.html(
        f"<script>/* {nonce} */"
        "(function () {"
        " try {"
        "  var m = window.parent.document.querySelector('section.stMain');"
        "  if (!m) { return; }"
        "  var go = function () { m.scrollTo({top: m.scrollHeight}); };"
        "  go(); setTimeout(go, 250); setTimeout(go, 900); setTimeout(go, 2000);"
        " } catch (e) {}"
        "})();</script>",
        height=0,
    )


def _submit_query(text: str):
    """Append the user's message and defer the (possibly slow) generation
    call to the next rerun, so the question renders as a chat bubble right
    away instead of staying hidden behind a frozen loading line for however
    long Ollama takes (up to ~200s on CPU-only hardware, see T25)."""
    now = _local(datetime.now(timezone.utc))
    st.session_state.messages.append({
        "role": "user",
        "content": text,
        "timestamp": now.strftime("%I:%M %p"),
        "timestamp_full": now.isoformat(),
    })
    session = get_active_session()
    if session:
        session["message_count"] = len(st.session_state.messages)
    st.session_state.pending_send = True
    st.session_state.query_state = text


def _send_message(text: str, append_user: bool = True):
    """Append a user message (optional) + AI response with full metadata."""
    if append_user:
        now = _local(datetime.now(timezone.utc))
        st.session_state.messages.append({
            "role": "user",
            "content": text,
            "timestamp": now.strftime("%I:%M %p"),
            "timestamp_full": now.isoformat(),
        })

    session = get_active_session()

    response = get_ai_response(text)
    if response.get("status_code") == 401:
        _end_expired_session()
        return
    # Name the chat after the first question that got an answer. A refused or failed
    # turn is not saved by the API, so it must not name a chat that will not exist
    # after a reload.
    if (session and not response.get("error_type")
            and session["title"] in ("New Chat", "Welcome Chat")):
        session["title"] = text[:40] + ("..." if len(text) > 40 else "")
    now2 = _local(datetime.now(timezone.utc))
    backend_session_id = response.get("session_id")
    if backend_session_id:
        st.session_state.session_id = backend_session_id
        if session:
            session["backend_session_id"] = backend_session_id
            session["course_id"] = _active_course()
        _remember_chat_selection()

    msg = {
        "role": "assistant",
        "content": response.get("answer", ""),
        "source_references": response.get("source_references", []),
        "confidence": response.get("confidence"),
        "confidence_score": response.get("confidence_score"),
        # T8-07: defaulting to a model name the host stopped using in Sprint 8
        # meant a failed answer was labelled as if llama3 had produced it.
        "model_used": response.get("model_used") or "unknown",
        "token_count": response.get("token_count"),
        "latency_ms": response.get("latency_ms"),
        "is_fallback": response.get("is_fallback", False),
        "from_api": response.get("from_api", False),
        "backend_mode": response.get("backend_mode"),
        "retrieval_metadata": response.get("retrieval_metadata"),
        "response_style": response.get("response_style"),
        "error_type": response.get("error_type"),
        "error_message": response.get("error_message"),
        "timestamp": now2.strftime("%I:%M %p"),
        "timestamp_full": now2.isoformat(),
    }
    st.session_state.messages.append(msg)

    # Update session message count
    if session:
        session["message_count"] = len(session["messages"])


# Joining is a student action: POST /api/courses/<code>/join refuses anyone else
# (src/api/routes/courses.py). A lecturer is added to a course by an
# administrator, so staff are told that instead of being offered a Join button
# that can only fail.
_STAFF_COURSE_HINT = ("Lecturers are added to a course by an administrator. "
                      "Ask an administrator to add you to the courses you teach.")


def _no_course_hint(role) -> str:
    """One line saying what to do when the account has no course."""
    role = str(role or "").lower()
    if role == "lecturer":
        return "Ask an administrator to add you to a course."
    if role == "admin":
        return "No active courses yet. Create or reactivate one in the Admin Dashboard."
    return "Join a course in My Courses to view its materials."


def _render_no_courses_notice() -> None:
    """Shown instead of the chat when the account is enrolled in nothing.

    Students can browse available courses and join before asking questions.
    Lecturers wait to be added by an administrator, and an administrator who
    sees this has no active course at all.
    """
    role = str((st.session_state.get("user") or {}).get("role", "Student")).lower()
    st.markdown("### 💬 Ask your course materials")
    if role == "lecturer":
        st.info("**You are not assigned to any course yet.**")
        st.write(_STAFF_COURSE_HINT)
        st.caption("Nothing is wrong with your account - it just has no courses on it.")
    elif role == "admin":
        st.info("**There are no active courses yet.**")
        st.write("Create a course, or reactivate one, in the Admin Dashboard.")
        if st.button("Open Admin Dashboard", key="open_admin_empty", type="primary"):
            st.session_state.current_page = "admin"
            st.rerun()
    else:
        st.info(
            "**You are not enrolled in any course yet.**"
        )
        st.write(
            "Open My Courses and join an available course to start asking questions."
        )
        st.caption("Nothing is wrong with your account - it just has no courses on it.")
        if st.button("Browse courses", key="browse_courses_empty", type="primary"):
            st.session_state.current_page = "courses"
            st.rerun()


def render_chat_page():
    # Taken at once so the request cannot outlive the run that was meant to
    # honour it, whichever way this run leaves.
    scroll_after_answer = bool(st.session_state.pop("scroll_after_answer", False))
    if not _course_options_for_user(st.session_state.get("user") or {}):
        _render_no_courses_notice()
        return

    active_cid = _reconcile_active_course()
    session = get_active_session()
    # Only a local chat may acquire its first course. Persisted conversations
    # retain their original course, including a legacy missing course.
    if not session.get("course_id") and not session.get("backend_session_id"):
        session["course_id"] = active_cid
    elif session.get("course_id") != active_cid:
        # Store the notice before updating URL state so it survives reruns.
        session = create_new_session(course_transition=True)

    if session.get("course_transition_notice"):
        if st.button("Dismiss notification", key="dismiss_course_transition"):
            session["course_transition_notice"] = False
            st.rerun()
        else:
            st.info("This conversation cannot continue in the selected course. "
                    "A new chat has been opened; the previous conversation is unchanged.")

    col1, col2, col3, col4, col5 = st.columns([4, 3, 2, 2, 2])
    with col1:
        st.markdown("### 💬 Ask your course materials")
        st.caption(f"Querying **{_course_display_label(active_cid)}**")
    with col2:
        # Fetch materials for the course displayed in the header.
        live_docs = api.get_documents(active_cid)
        indexed_live = _document_indexed_count(live_docs)
        # Show the model reported by the last answer, or a neutral API label
        # before the first answer arrives.
        model_label = "Live API" if api.is_live else "Offline"
        for _msg in reversed(st.session_state.get("messages", [])):
            if _msg.get("role") == "assistant" and _msg.get("model_used") and not _msg.get("error_type"):
                model_label = _msg["model_used"]
                break
        st.markdown(
            f"<span class='status-badge badge-ready'>{indexed_live} docs indexed</span> "
            f"{get_model_badge(model_label)}",
            unsafe_allow_html=True,
        )
    with col3:
        course_options = st.session_state.get("course_options") or COURSE_FALLBACKS
        if active_cid not in course_options:
            course_options = [active_cid] + list(course_options)
        # Widget keys can be discarded when the login page reruns. Reconcile
        # immediately before declaration, and default to the course the rest of
        # the page is using, so the picker cannot come up empty while the header
        # beside it names a course.
        st.session_state.selected_course_id = active_cid
        selected_course = st.selectbox(
            "Course",
            course_options,
            index=course_options.index(active_cid),
            format_func=_course_display_label,
            label_visibility="collapsed",
            key="selected_course_id",
            on_change=_change_chat_course,
        )
    with col4:
        # T8-11: Response-style picker — fetched from GET /api/response-styles.
        # "Auto" (empty string) means "use whatever the course is configured
        # for" and is the default so students don't accidentally override a
        # lecturer's setting just by loading the page.
        if st.session_state.get("response_styles_cache") is None:
            st.session_state.response_styles_cache = api.get_response_styles()
        styles_data = st.session_state.response_styles_cache
        style_list = styles_data.get("styles") or []
        if style_list:
            options = [""] + [s["id"] for s in style_list]
            labels = {"": "Auto (course default)"}
            labels.update({s["id"]: s.get("label", s["id"]) for s in style_list})
            current = st.session_state.get("response_style") or ""
            if current not in options:
                current = ""
            chosen = st.selectbox(
                "Style",
                options,
                index=options.index(current),
                format_func=lambda sid: labels.get(sid, sid),
                label_visibility="collapsed",
                key="response_style_select",
            )
            st.session_state.response_style = chosen or None
    with col5:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = None
            if session:
                session["messages"] = []
                session["message_count"] = 0
                session["backend_session_id"] = None
            _remember_chat_selection()
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
                        _submit_query(prompt)
                        st.rerun()
        else:
            for msg in st.session_state.messages:
                timestamp_str = msg.get("timestamp", "")

                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="clearfix"><div class="user-msg">'
                        f'{_html.escape(msg["content"])}'
                        f'<div class="msg-time">{timestamp_str}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Check for error state (T10)
                    if msg.get("error_type"):
                        st.markdown(
                            f'<div class="error-card">'
                            f'<strong>⚠️ Could not get an answer</strong><br>'
                            f'{_html.escape(str(msg.get("error_message") or "An error occurred."))}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        continue

                    # Escaped before any markup is added. The answer text comes
                    # from the model, which is fed the contents of uploaded
                    # documents, so a document carrying an injection could
                    # otherwise put working script into every reader's page.
                    # Bold and code spans are re-applied afterwards so the
                    # intended formatting still renders.
                    is_fallback = msg.get("is_fallback", False)
                    # The pipeline prefixes a fallback answer with this same
                    # sentence, so rendering the banner on top of it showed the
                    # reader the warning twice. The banner is the better of the
                    # two -- it is styled and it cannot be mistaken for the
                    # model's own words -- so the prefix comes off here.
                    body = _strip_fallback_prefix(msg["content"]) if is_fallback else msg["content"]

                    answer_html = _html.escape(body).replace("\n", "<br>")
                    answer_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', answer_html)
                    answer_html = re.sub(r'`([^`]+)`', r'<code>\1</code>', answer_html)

                    fallback_html = ""
                    if is_fallback:
                        fallback_html = '<div class="fallback-label">⚠️ Based on general knowledge — not verified against course materials</div>'

                    # Source chips with ChromaDB metadata (T10)
                    sources_html = ""
                    if msg.get("source_references"):
                        sources_html = '<div class="source-label">📄 Retrieved from:</div>'
                        # Numbered, because the answer cites [S1], [S2]... and an
                        # unnumbered list gives the reader nothing to match them
                        # against. The pipeline renumbers the markers to these
                        # very positions, so chip n is always marker [Sn].
                        for position, src in enumerate(msg["source_references"], 1):
                            # Filenames, sections and collection names come from
                            # uploaded material, so they are attacker-chosen in
                            # the same way the answer text is.
                            filename = _html.escape(str(
                                src.get("filename") or src.get("source_file")
                                or src.get("source") or "Document"))
                            page_number = _html.escape(str(
                                src.get("page_number") or src.get("page") or "?"))
                            section = _html.escape(str(src.get("section") or src.get("topic") or ""))
                            section_str = f" · {section}" if section else ""
                            collection = _html.escape(str(src.get("collection_name", "")))
                            collection_str = f" [{collection}]" if collection else ""
                            sim_pct = int((src.get("similarity") or 0) * 100)
                            sources_html += (
                                f'<span class="source-chip">'
                                f'<strong>[S{position}]</strong> {filename} · p.{page_number}'
                                f'{section_str} · {sim_pct}%{collection_str}'
                                f'</span>'
                            )

                    confidence = _confidence_score(msg.get("confidence"), msg.get("confidence_score"))
                    # Label and colour come from one band, so they cannot disagree.
                    band = _confidence_band(msg.get("confidence"), msg.get("confidence_score"))
                    conf_color = _BAND_COLOURS.get(band, _BAND_COLOURS["Low"])
                    conf_pct = int(confidence * 100)
                    conf_label = f"{band} confidence" if band else "No confidence data"
                    has_confidence = msg.get("confidence") is not None or msg.get("confidence_score") is not None
                    confidence_html = (
                        f'<div class="confidence-bar"><div class="confidence-fill" '
                        f'style="width: {conf_pct}%; background: {conf_color};"></div></div>'
                        if has_confidence else ""
                    )
                    confidence_text = f"{conf_label}: {conf_pct}%" if has_confidence else "Confidence unavailable"
                    if "is_fallback" not in msg:
                        confidence_text += " · Fallback status unavailable"
                    model_used = msg.get("model_used", "")
                    model_badge = get_model_badge(model_used)
                    msg_class = "ai-msg-fallback" if is_fallback else "ai-msg"
                    api_indicator = " · 🟢 Live API" if msg.get("from_api") else ""
                    latency_ms = msg.get("latency_ms")
                    latency_indicator = f" · ⏱️ {latency_ms / 1000:.1f}s" if isinstance(latency_ms, (int, float)) else ""

                    html_content = (
                        f'<div class="clearfix"><div class="{msg_class}">'
                        f'{fallback_html}{answer_html}{sources_html}'
                        f'{confidence_html}'
                        f'<div class="confidence-text">'
                        f'{confidence_text} · {model_badge}{latency_indicator} · {timestamp_str}{api_indicator}'
                        f'</div>'
                        f'</div></div>'
                    )
                    st.markdown(html_content, unsafe_allow_html=True)

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
                        _submit_query(prompt)
                        st.rerun()

    # ── Input bar ──
    st.markdown("<br>", unsafe_allow_html=True)

    user_input = st.chat_input("Ask a question about your course materials...")

    if user_input and user_input.strip():
        _submit_query(user_input.strip())
        st.rerun()

    # Generation happens here, one rerun after the user's message was
    # appended above, so the question is already visible as a chat bubble
    # instead of hiding behind the welcome screen for the whole wait (T11).
    if st.session_state.pending_send:
        st.session_state.pending_send = False
        pending_query = st.session_state.query_state
        st.session_state.query_state = None

        state_placeholder = st.empty()
        state_placeholder.markdown(
            '<div class="query-state"><div class="dot"></div> '
            '🧠 Generating response... (can take up to a couple of minutes '
            'on CPU-only hardware)</div>',
            unsafe_allow_html=True,
        )
        # Bring the new question and the waiting line into view before the
        # (slow) model call, then again once the answer has been drawn.
        _scroll_to_latest()
        _send_message(pending_query, append_user=False)
        state_placeholder.empty()
        st.session_state.scroll_after_answer = True
        st.rerun()

    if scroll_after_answer:
        _scroll_to_latest()


# ─── SESSION HISTORY PAGE ──────────────────────────────────────────

def render_history_page():
    st.markdown("### 📋 Session History")

    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        # Was hardcoded to ["All courses", "CSIT321", "CSIT214", "ISIT312"];
        # ISIT312 is not a real course on this instance.
        _user = st.session_state.get("user") or {}
        course_filter = st.selectbox(
            "Course", ["All courses"] + _course_options_for_user(_user),
            key="history_course", label_visibility="collapsed")
    with col2:
        period_filter = st.selectbox(
            "Period", ["Last 7 days", "Last 30 days", "All time"],
            key="history_period", label_visibility="collapsed")
    with col3:
        search_text = st.text_input(
            "Search", placeholder="🔍 Search conversations...",
            key="history_search", label_visibility="collapsed")

    st.divider()

    # Combine real sessions with demo data
    real_sessions = _history_sessions(st.session_state.get("sessions", []))
    # Four invented conversations used to be merged in here unconditionally,
    # so every user saw the same fake history on their own account (T8-07).
    # All three controls above used to be rendered with their return values
    # discarded, so "Last 7 days" listed conversations from weeks earlier and a
    # nonsense search term still returned every session.
    all_sessions = _filter_sessions(real_sessions, course_filter, period_filter, search_text)
    accent_colors = ["#0D9488", "#1B2A4A", "#D4A843", "#0D9488", "#64748B"]

    if not all_sessions:
        st.info("No conversations match these filters." if real_sessions
                else "No conversations yet.")

    # Older conversations used to be unreachable: the loop stopped at eight and
    # nothing offered the rest.
    shown = int(st.session_state.get("history_shown", _HISTORY_PAGE))
    visible = all_sessions[:shown]

    for i, session in enumerate(visible):
        title = _html.escape(session.get("title", "Untitled"))
        course = _html.escape(session.get("course_id", "CSIT214"))
        created = _html.escape(session.get("created_at", "—"))
        msg_count = _saved_message_count(session.get("messages"))
        preview = _html.escape(session.get("preview", f"{msg_count} messages in this session"))
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
                switch_session(session["session_id"])
                st.session_state.current_page = "chat"
                st.rerun()
        with c3:
            if st.button("Delete", key=f"delete_{i}", type="secondary"):
                backend_sid = session.get("backend_session_id")
                # Local-only chats (no backend ID yet) are just removed in-memory
                if backend_sid:
                    result = api.delete_session(backend_sid)
                    ok = result.get("success")
                    err = result.get("error", "unknown error")
                else:
                    ok, err = True, None

                if ok:
                    sid = session["session_id"]
                    was_active = st.session_state.get("active_session_id") == sid
                    st.session_state.sessions = [
                        s for s in st.session_state.sessions
                        if s["session_id"] != sid
                    ]
                    if was_active:
                        remaining = st.session_state.sessions
                        if remaining:
                            switch_session(remaining[-1]["session_id"])
                        else:
                            create_new_session()
                    st.rerun()
                else:
                    st.toast(f"Could not delete: {err}")

    if all_sessions:
        st.caption(f"Showing {len(visible)} of {len(all_sessions)} conversations.")
    if len(all_sessions) > len(visible):
        if st.button(f"Show {min(_HISTORY_PAGE, len(all_sessions) - len(visible))} more",
                     key="history_show_more"):
            st.session_state.history_shown = len(visible) + _HISTORY_PAGE
            st.rerun()


# ─── UPLOADS PAGE (Student view) ──────────────────────────────────

def render_uploads_page():
    if not _active_course():
        _render_no_courses_notice()
        return
    # Students can read materials; upload and removal belong to lecturers.
    st.markdown("### 📚 Course Materials")
    st.caption("Everything your lecturer has added for this course. Open any of "
               "them to read; only a lecturer can add or remove them.")
    _render_document_table(student_view=True)


# ─── DOCUMENT MANAGER (Lecturer / Admin view) ──────────────────────

def render_doc_manager_page():
    st.markdown("### 📁 Document Manager")
    role = st.session_state.user.get("role", "Student")
    st.markdown(f"<span class='status-badge badge-processing'>{role} View</span>", unsafe_allow_html=True)

    course_options = st.session_state.get("course_options") or _course_options_for_user(st.session_state.user)
    current_course = _active_course()
    if not current_course:
        st.info("You are not in any course yet, so there is nothing to manage here. "
                + _no_course_hint(role))
        return
    if current_course not in course_options:
        course_options = [current_course] + list(course_options)

    col_sel, col_refresh = st.columns([4, 2])
    with col_sel:
        st.markdown("**Target course for upload**")
        selected_course = st.selectbox(
            "Course",
            course_options,
            index=course_options.index(current_course),
            format_func=_course_display_label,
            label_visibility="collapsed",
            key="doc_manager_course_select",
        )
    with col_refresh:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("🔄 Refresh Status", type="primary", use_container_width=True):
            st.rerun()

    if selected_course != st.session_state.get("course_id"):
        st.session_state.course_id = selected_course
        st.session_state.selected_course_id = selected_course
        st.rerun()

    st.caption(f"Uploads will be indexed under **{_course_display_label(selected_course)}**.")

    uploaded_files = st.file_uploader(
        "Upload course materials",
        type=list(_UPLOAD_TYPES),
        accept_multiple_files=True,
        help=_upload_help_text(),
    )
    _show_flashes("upload")

    if "processed_uploads" not in st.session_state:
        st.session_state.processed_uploads = set()

    if uploaded_files:
        for f in uploaded_files:
            file_key = f"{f.name}_{len(f.getvalue())}_{selected_course}"
            if file_key not in st.session_state.processed_uploads:
                _run_real_upload_and_indexing(f, selected_course)
                st.session_state.processed_uploads.add(file_key)
                st.rerun()

    st.divider()
    st.markdown("**UPLOADED DOCUMENTS**")
    _render_document_table(student_view=False)


MAX_UPLOAD_MB = 50

# The file types the API accepts (chunker.SUPPORTED_EXTENSIONS). The help text is built from
# this tuple so the two cannot drift apart; a test compares it with the chunker.
_UPLOAD_TYPES = ("pdf", "pptx", "docx")


def _upload_help_text() -> str:
    names = ", ".join(t.upper() for t in _UPLOAD_TYPES[:-1]) + f" or {_UPLOAD_TYPES[-1].upper()}"
    return f"Drag and drop {names} files here. Max {MAX_UPLOAD_MB} MB per file."


def _run_real_upload_and_indexing(f, course_id):
    filename = f.name
    file_bytes = f.getvalue()
    file_size = len(file_bytes)

    progress_placeholder = st.empty()

    # Checked here rather than only server-side. Past MAX_CONTENT_LENGTH the
    # server stops reading and closes the socket while the client is still
    # sending, so the uploader sees a connection error instead of the 413 and
    # retries the same file. Catching it before the request avoids the race.
    if file_size == 0:
        _flash(f"{filename} is empty (0 bytes). Check it saved correctly.", "error", "upload")
        return
    if file_size > MAX_UPLOAD_MB * 1024 * 1024:
        _flash(f"{filename} is {file_size / (1024*1024):.0f} MB. "
               f"The limit is {MAX_UPLOAD_MB} MB - split it or compress it first.", "error", "upload")
        return
    progress_placeholder.info(f"Uploading {filename}...")

    res = api.upload_document(file_bytes, filename, course_id)
    if res.get("status_code") == 401:
        _end_expired_session()
        return
    if not res.get("success"):
        _flash(f"❌ Upload failed: {res.get('error', 'Unknown error')}", "error", "upload")
        return

    job_id = res.get("job_id")
    if not job_id:
        _flash(f"✅ {filename} — uploaded successfully!", "success", "upload")
        return

    stages = {
        "queued": "⏳ Queued in system...",
        "processing": "🧠 Ingesting (extracting text, chunking, embedding)...",
        "completed": "✅ Completed",
        "failed": "❌ Failed",
    }

    while True:
        status_res = api.get_indexing_status(job_id)
        status = str(status_res.get("status", "queued")).lower()
        progress = status_res.get("progress_percent", 0)

        if status == "completed":
            _flash(f"✅ {filename} — uploaded and indexed successfully!", "success", "upload")
            break
        elif status == "unavailable":
            _flash((status_res.get("error") or "Indexing status is unavailable.")
                   + " The upload was accepted, but indexing could not be confirmed. "
                   "Check the document list before uploading again.", "warning", "upload")
            break
        elif status == "failed":
            err_msg = status_res.get("error", "Unknown indexing error")
            _flash(f"❌ Indexing failed for {filename}: {err_msg}", "error", "upload")
            break
        else:
            msg = stages.get(status, "⏳ Processing...")
            progress_placeholder.markdown(
                f'<div class="upload-progress"><strong>{_html.escape(filename)}</strong> ({file_size / 1024:.1f} KB)<br>'
                f'<div class="upload-step upload-step-active">{msg} ({progress}%)</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            time.sleep(1.0)


def _document_table_ratio(student_view: bool):
    """Column shares for the document table.

    Status and Actions used to take a `1` share each. Below roughly 1200px that
    left the Status cell too narrow for the word "Indexed" -- it wrapped to one
    character per line and drove the row to 83px -- and the Actions cell too
    narrow for its buttons, which then overflowed their own container.
    """
    # ..., Open for everyone, then Delete for a lecturer.
    return [3.5, 1, 1, 2, 2, 1.2] + ([1.2] if not student_view else [])


def _document_indexed_count(docs) -> int:
    """How many documents are actually usable in an answer.

    One rule, used by the table, the summary line, the sidebar and the chat
    header. They each had their own before, so the same course could be
    reported as 7 indexed in one place and 6 in another.
    """
    return sum(1 for d in (docs or []) if _document_status(d)[0] == "indexed")


# A job orphaned by an API restart stays queued or processing forever; nothing
# recovers it. Past this age a waiting row is shown as stalled instead.
_STALLED_AFTER_MINUTES = 15


def _document_age_minutes(doc):
    """Minutes since the upload, or None when the timestamp is missing or unreadable."""
    stamp = doc.get("uploaded_at") or doc.get("uploaded")
    if not stamp:
        return None
    when = _local(stamp)
    if when is None:
        return None
    try:
        return (datetime.now(timezone.utc) - when).total_seconds() / 60
    except TypeError:
        return None


_STATUS_DOT = {"badge-indexed": "#10B981", "badge-processing": "#F59E0B", "badge-pending": "#94A3B8"}


def _document_status_dot(doc) -> str:
    """Sidebar dot colour, derived from the same badge the table shows."""
    return _STATUS_DOT.get(_document_status(doc)[1], "#EF4444")


def _document_status(doc):
    """(label, badge class, tooltip) for one document.

    A row whose `status` column says "indexed" while it holds no chunks is not
    indexed in any sense the reader cares about: it can never be retrieved or
    cited. Reporting it as ready is how a document sat in the corpus for months
    looking healthy while contributing nothing to a single answer.
    """
    raw = str(doc.get("status") or doc.get("indexing_status") or "pending").lower()
    chunks = doc.get("chunks") or 0

    if raw in ("indexed", "completed"):
        if chunks:
            # "recorded" rather than "in the vector store": this reads the count
            # stored with the document, not ChromaDB itself.
            return "indexed", "badge-indexed", f"{chunks} chunks recorded"
        if chunks is None:
            return ("no chunks", "badge-failed",
                    "No chunk count recorded, so it cannot be cited. Re-upload it.")
        return ("no chunks", "badge-failed",
                "Marked indexed but holds no chunks, so it can never be cited. Re-upload it.")
    if raw in ("pending", "queued", "processing"):
        age = _document_age_minutes(doc)
        if age is not None and age > _STALLED_AFTER_MINUTES:
            return ("stalled", "badge-failed",
                    f"Indexing has not finished after {_STALLED_AFTER_MINUTES} minutes. Re-upload it.")
        if raw == "processing":
            return "processing", "badge-processing", "Indexing is still running"
        return raw, "badge-pending", "Queued for indexing"
    return raw, "badge-failed", f"Indexing status: {raw}"


def _document_totals(docs) -> tuple[int, int]:
    """Counts for the Document Manager summary line.

    `chunks` is NULL for every document that failed to index, and
    `.get("chunks", 0)` hands back that None rather than the default - the key
    is present, it just has no value. Summing then raised TypeError and took
    the whole page down, so one bad upload hid every good one. `file_size_bytes`
    just above already had this right.
    """
    # Counted the same way the badge decides, so the summary line cannot say
    # "5 indexed" while one row on screen reads "Not indexed".
    indexed = _document_indexed_count(docs)
    total_chunks = sum((d.get("chunks") or 0) for d in docs)
    return indexed, total_chunks


def _render_document_table(student_view: bool = False):
    """Render document list with status badges (shared by uploads + doc manager)."""
    # Both student and lecturer views require an available course.
    course_id = _active_course()
    if not course_id:
        st.caption("Join a course to see its materials.")
        return
    docs = api.get_documents(course_id)

    headers = ["File Name", "Type", "Size", "Status", "Uploaded", "Open"]
    if not student_view:
        headers.append("Remove")
    cols = st.columns(_document_table_ratio(student_view))
    for col, header in zip(cols, headers):
        # A header that breaks mid-word ("Stat us", "Typ e") reads as a glitch.
        col.markdown(
            f"<strong style='white-space: nowrap;'>{header}</strong>",
            unsafe_allow_html=True)
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)

    for doc in docs:
        doc_id = doc.get("document_id") or doc.get("id") or "unknown"
        doc_name = doc.get("original_filename") or doc.get("filename") or "Unknown"
        doc_type = doc.get("file_type") or doc_name.rsplit(".", 1)[-1] if "." in doc_name else "unknown"
        doc_type = str(doc_type).upper()
        if "/" in doc_type:
            doc_type = doc_type.split("/")[-1].replace("VND.OPENXMLFORMATS-OFFICEDOCUMENT.PRESENTATIONML.PRESENTATION", "pptx").replace("VND.OPENXMLFORMATS-OFFICEDOCUMENT.WORDPROCESSINGML.DOCUMENT", "docx")
        doc_type = _html.escape(doc_type)

        size_bytes = doc.get("file_size_bytes") or doc.get("size_bytes") or 0
        doc_size = f"{size_bytes / (1024*1024):.1f} MB" if size_bytes else "—"

        status, badge_class, status_note = _document_status(doc)

        uploaded_at = doc.get("uploaded_at") or doc.get("uploaded") or "—"
        uploaded_local = _local(uploaded_at)
        doc_uploaded = uploaded_local.strftime("%Y-%m-%d") if uploaded_local else "—"

        cols = st.columns(_document_table_ratio(student_view))
        cols[0].markdown(f"📄 {doc_name}")
        cols[1].markdown(f"<span style='color: #475569;'>{doc_type}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span style='color: #475569;'>{doc_size}</span>", unsafe_allow_html=True)
        cols[3].markdown(
            f"<span class='status-badge {badge_class}' title='{_html.escape(status_note)}'>"
            f"{status.capitalize()}</span>", unsafe_allow_html=True)
        cols[4].markdown(f"<span style='color: #475569;'>{doc_uploaded}</span>", unsafe_allow_html=True)
        # Reading the original file. Fetched only when asked for: some of these
        # run to 11 MB, and pulling every one on every rerun to keep a download
        # control primed would make the page unusable.
        if st.session_state.get("doc_open") == doc_id:
            result = api.download_document(doc_id)
            if result.get("success"):
                cols[5].download_button(
                    "⬇️", data=result["content"], file_name=doc_name,
                    key=f"dl_{doc_id}", help=f"Save {doc_name}")
            else:
                # Say which of the several reasons it was. Reporting an expired
                # session as a missing file sends the reader after the wrong
                # problem, and there is nothing they can do about a file that is
                # supposedly gone.
                st.warning(f"{doc_name}: {result.get('error')}")
                st.session_state.doc_open = None
        elif cols[5].button("📄", key=f"open_{doc_id}", help=f"Open {doc_name}"):
            st.session_state.doc_open = doc_id
            st.rerun()

        if not student_view:
            # The retry button that used to sit here called nothing -- its
            # return value was discarded, and there is no re-index route to
            # call anyway. A control that cannot work is worse than no control,
            # so re-indexing means re-uploading the file until that route
            # exists. Deleting is now confirmed, and its result is checked:
            # a failed delete used to look exactly like a successful one.
            if st.session_state.get("confirm_doc_delete") == doc_id:
                st.warning(f"Delete {doc_name}? This removes it and its chunks for everyone.")
                yes_col, no_col = cols[6].columns(2)
                if yes_col.button("✓", key=f"deldoc_yes_{doc_id}", help="Confirm delete"):
                    result = api.delete_document(doc_id)
                    st.session_state.confirm_doc_delete = None
                    if isinstance(result, dict) and result.get("success") is False:
                        st.error(result.get("error") or f"Could not delete {doc_name}.")
                    else:
                        st.toast(f"Deleted {doc_name}.")
                        st.rerun()
                if no_col.button("✕", key=f"deldoc_no_{doc_id}", help="Cancel"):
                    st.session_state.confirm_doc_delete = None
                    st.rerun()
            elif cols[6].button("🗑️", key=f"delmgr_{doc_id}", help=f"Delete {doc_name}"):
                st.session_state.confirm_doc_delete = doc_id
                st.rerun()

    st.divider()
    indexed, total_chunks = _document_totals(docs)
    st.caption(f"{len(docs)} documents · {indexed} indexed · {total_chunks} chunks")
    # Only rows the badge calls failed: an upload that is still queued or processing
    # has no chunks yet and must not be told to re-upload.
    unindexed = [d for d in docs if _document_status(d)[1] == "badge-failed"]
    if unindexed and not student_view:
        st.warning(
            f"{len(unindexed)} document(s) have no indexed chunks and cannot be cited in "
            "an answer: " + ", ".join(
                str(d.get("original_filename") or d.get("filename") or "?") for d in unindexed
            ) + ". Re-upload to index them."
        )


# ─── SETTINGS / LIVE CONFIG (Lecturer / Admin view) ────────────────

# T8-09. The backend (T8-08) resolves every value as
#     course override  ->  global setting  ->  environment default
# and this page has to show which of those three a number came from. Without
# that, a lecturer reads an inherited global value as their own course's
# setting, changes something else, and cannot explain why the first number
# moved. The badge next to each control is the whole point of the screen.

_COURSE_SCOPED_KEYS = ("top_k", "similarity_threshold", "response_style", "prompt_strategy")
_GLOBAL_ONLY_KEYS = ("ollama_model", "temperature", "num_predict")
_PROMPT_STRATEGIES = ("baseline", "evidence_cited", "few_shot_cited")

_KEY_HELP = {
    "top_k": "How many chunks retrieval hands the model. Measured on this host: "
             "5 to 8 moved an answer by about ten characters.",
    "similarity_threshold": "How close a chunk must be to count as relevant. "
                            "Raise it for fewer, safer sources; lower it if good "
                            "material is being missed. Above roughly 0.9 nothing "
                            "qualifies and every answer falls back.",
    "response_style": "How answers are written for this course. Students can still "
                      "pick their own per question.",
    "prompt_strategy": "Which prompt template builds the request. evidence_cited "
                       "forces inline [S#] citations; few_shot_cited adds one "
                       "worked example, which helps smaller models copy the format.",
    "ollama_model": "Which model is resident in the shared 16 GB of VRAM. Changing "
                    "this evicts the current one for everybody, which is why it is "
                    "admin-only and not per course.",
    "temperature": "Higher is more varied, lower is more repeatable. 0.2 is the "
                   "current default and suits factual answering.",
    "num_predict": "Maximum tokens in an answer. Raising it did not lengthen "
                   "answers on this host; response_style is what changes length.",
}


_OTHER_MODEL = "Other (type a name)…"


def _model_picker(stored_value, known_models, *, disabled, effective=None):
    """Pick the model from the ones we have measured, without locking the admin in.

    The catalogue comes from the API so the notes stay with the validation that
    accepts them. A model already set but not in the catalogue stays selectable,
    and "Other" is always there for something freshly pulled -- otherwise this
    screen would refuse to show a value the API is perfectly happy to store.
    """
    if not known_models:
        # Fixtures, or the API is down: no catalogue to offer, so keep the box.
        return st.text_input(
            "Model", value=str(stored_value or ""), disabled=disabled,
            key="gval_ollama_model", label_visibility="collapsed",
        )

    notes = {m["name"]: m.get("note", "") for m in known_models}
    options = [m["name"] for m in known_models]
    if stored_value and stored_value not in options:
        options.insert(0, str(stored_value))
    options.append(_OTHER_MODEL)

    # With nothing stored, the value in effect comes from the environment, not
    # from whichever catalogue entry happens to sort first. Showing the first
    # entry told an admin on a smaller host that it was serving a model it was
    # not.
    fallback = str(effective) if effective else options[0]
    if fallback not in options:
        options.insert(0, fallback)
    current = str(stored_value) if stored_value else fallback
    choice = st.selectbox(
        "Model", options, index=options.index(current),
        disabled=disabled, key="gval_ollama_model", label_visibility="collapsed",
    )
    if choice == _OTHER_MODEL:
        return st.text_input(
            "Model name", value="", disabled=disabled,
            key="gval_ollama_model_custom", placeholder="name:tag as `ollama pull` takes it",
        ).strip()
    if notes.get(choice):
        st.caption(notes[choice])
    return choice


_HISTORY_PAGE = 8
_PERIOD_DAYS = {"Last 7 days": 7, "Last 30 days": 30, "All time": None}


def _session_moment(session):
    """Best-effort timestamp for a session, or None if it cannot be read.

    None means "keep it". Hiding a conversation because its timestamp arrived
    in an unexpected shape is a worse failure than showing one too many.
    """
    raw = str(session.get("created_at") or "").strip().replace("T", " ").rstrip("Z")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _session_haystack(session) -> str:
    """Everything in a session that a search should look at."""
    parts = [str(session.get("title", "")), str(session.get("preview", "")),
             str(session.get("course_id", ""))]
    for m in session.get("messages") or []:
        parts.append(str(m.get("question", "")))
        parts.append(str(m.get("answer", "")))
        parts.append(str(m.get("content", "")))
    return " ".join(parts).lower()


def _saved_message_count(messages) -> int:
    """Messages in exchanges the server stored.

    A turn that came back as an error was never saved (src/api/routes/query.py), so
    it is not counted: after a reload it is gone, and the count should say the same.
    """
    answered = sum(1 for m in (messages or [])
                   if m.get("role") == "assistant" and not m.get("error_type"))
    return 2 * answered


def _history_sessions(sessions):
    """Conversations worth listing in Session History: at least one saved exchange."""
    return [s for s in (sessions or []) if _saved_message_count(s.get("messages")) > 0]


def _filter_sessions(sessions, course, period, query):
    """Apply the three Session History controls."""
    out = list(sessions or [])

    if course and course != "All courses":
        out = [s for s in out if s.get("course_id") == course]

    days = _PERIOD_DAYS.get(period)
    if days:
        cutoff = _local(datetime.now(timezone.utc)).replace(tzinfo=None) - timedelta(days=days)
        out = [s for s in out
               if (_session_moment(s) or cutoff) >= cutoff]

    needle = (query or "").strip().lower()
    if needle:
        out = [s for s in out if needle in _session_haystack(s)]

    return out


_FALLBACK_SENTENCE = "Based on general knowledge"


def _strip_fallback_prefix(text: str) -> str:
    """Drop the pipeline's leading fallback sentence, if it is there.

    Matched on the opening words rather than the exact string: the sentence has
    already been written with both an em dash and a hyphen, and a reader seeing
    the warning twice is a worse outcome than a missed strip.
    """
    lines = (text or "").lstrip().split("\n")
    if lines and lines[0].strip().startswith(_FALLBACK_SENTENCE):
        return "\n".join(lines[1:]).lstrip()
    return text


def _setting_source(key: str, course_stored: dict, global_stored: dict) -> tuple[str, bool]:
    """Where the value in effect for `key` actually comes from.

    Returns (label, is_course_override).
    """
    if key in course_stored:
        return "this course", True
    if key in global_stored:
        return "global", False
    return "default", False


def _source_badge(label: str) -> str:
    colour = {"this course": "#0F766E", "global": "#6366F1", "default": "#94A3B8"}[label]
    return (f'<span style="background:{colour}1A;color:{colour};font-size:0.7rem;'
            f'padding:1px 7px;border-radius:3px;letter-spacing:.03em;">{label}</span>')


def _render_course_tuning(course_code: str, styles: list, style_default: str | None):
    """Per-course retrieval settings, for the lecturer who owns this course."""
    course_cfg = api.get_course_settings(course_code)
    global_cfg = api.get_global_settings()

    if course_cfg.get("_unavailable") or global_cfg.get("_unavailable"):
        st.warning(
            "Settings need the database backend, which is not reachable right now. "
            "Values below would not save."
        )
        return

    stored = course_cfg.get("settings") or {}
    effective = course_cfg.get("effective") or {}
    global_stored = global_cfg.get("settings") or {}

    style_ids = [s.get("id") for s in styles] or [
        "concise", "detailed", "simple", "exam_prep", "socratic"
    ]
    style_labels = {s.get("id"): s.get("label", s.get("id")) for s in styles}

    # Deliberately not st.form: inside a form a checkbox does not trigger a
    # rerun until submit, so "Set for this course" could not enable the
    # control beside it -- the page rendered controls that stayed greyed
    # out no matter what you clicked. Plain widgets rerun on change; the
    # Save button below still sends everything in one request.
    changes: dict = {}
    with st.container():

        for key in _COURSE_SCOPED_KEYS:
            label, _is_override = _setting_source(key, stored, global_stored)
            current = effective.get(key)

            head, badge = st.columns([3, 1])
            head.markdown(f"**{key.replace('_', ' ').title()}**")
            badge.markdown(_source_badge(label), unsafe_allow_html=True)
            st.caption(_KEY_HELP[key])

            override = st.checkbox(
                "Set for this course",
                value=key in stored,
                key=f"ovr_{course_code}_{key}",
                help="Unticked, this course follows the global setting.",
            )

            if key == "top_k":
                value = st.number_input(
                    "Chunks retrieved", min_value=1, max_value=20,
                    value=int(current if current is not None else 5), step=1,
                    disabled=not override, key=f"val_{course_code}_{key}",
                    label_visibility="collapsed",
                )
            elif key == "similarity_threshold":
                value = st.slider(
                    "Similarity threshold", min_value=0.0, max_value=1.0,
                    value=float(current if current is not None else 0.35), step=0.01,
                    disabled=not override, key=f"val_{course_code}_{key}",
                    label_visibility="collapsed",
                )
            elif key == "response_style":
                options = style_ids
                idx = options.index(current) if current in options else 0
                value = st.selectbox(
                    "Response style", options, index=idx,
                    format_func=lambda s: style_labels.get(s, s),
                    disabled=not override, key=f"val_{course_code}_{key}",
                    label_visibility="collapsed",
                )
            else:  # prompt_strategy
                options = list(_PROMPT_STRATEGIES)
                idx = options.index(current) if current in options else 0
                value = st.selectbox(
                    "Prompt strategy", options, index=idx,
                    disabled=not override, key=f"val_{course_code}_{key}",
                    label_visibility="collapsed",
                )

            if override:
                changes[key] = value
            elif key in stored:
                # Was overridden, now unticked: null clears it so the value
                # falls back to the global setting, not to a hardcoded default.
                changes[key] = None

            st.divider()

        if st.button(f"Save {course_code} settings", type="primary", key=f"save_{course_code}"):
            if not changes:
                st.info("Nothing changed.")
            else:
                result = api.update_course_settings(course_code, changes)
                if result.get("success"):
                    cleared = [k for k, v in changes.items() if v is None]
                    msg = f"Saved. In effect for {course_code} from the next question."
                    if cleared:
                        msg += f" Cleared: {', '.join(cleared)}."
                    _flash(msg, "success", f"tuning_{course_code}")
                    st.rerun()
                else:
                    st.error(result.get("error") or "Could not save these settings.")
        _show_flashes(f"tuning_{course_code}")


def _render_global_tuning(styles: list):
    """Global settings. Admin only — these apply to every course at once, and
    the model choice decides what is resident in shared VRAM."""
    global_cfg = api.get_global_settings()
    if global_cfg.get("_unavailable"):
        st.warning("Settings need the database backend, which is not reachable right now.")
        return

    stored = global_cfg.get("settings") or {}

    st.caption(
        "These apply everywhere. A course can override retrieval settings for "
        "itself; model, temperature and answer length stay global because they "
        "decide what sits in the shared GPU."
    )

    # Same reason as the per-course panel above.
    changes: dict = {}
    with st.container():

        for key in _GLOBAL_ONLY_KEYS:
            in_effect = key in stored
            head, badge = st.columns([3, 1])
            head.markdown(f"**{key.replace('_', ' ').title()}**")
            badge.markdown(
                _source_badge("global" if in_effect else "default"),
                unsafe_allow_html=True,
            )
            st.caption(_KEY_HELP[key])

            override = st.checkbox(
                "Set globally", value=in_effect, key=f"govr_{key}",
                help="Unticked, the value from the environment is used.",
            )

            if key == "ollama_model":
                value = _model_picker(
                    stored.get(key), global_cfg.get("known_models") or [],
                    disabled=not override,
                    effective=global_cfg.get("effective_model"),
                )
            elif key == "temperature":
                value = st.slider(
                    "Temperature", min_value=0.0, max_value=2.0,
                    value=float(stored.get(key, 0.2)), step=0.05,
                    disabled=not override, key=f"gval_{key}",
                    label_visibility="collapsed",
                )
            else:  # num_predict
                value = st.number_input(
                    "Max answer tokens", min_value=64, max_value=4096,
                    value=int(stored.get(key, 220)), step=32,
                    disabled=not override, key=f"gval_{key}",
                    label_visibility="collapsed",
                )

            if override:
                changes[key] = value
            elif in_effect:
                changes[key] = None

            st.divider()

        if st.button("Save global settings", type="primary", key="save_global"):
            if not changes:
                st.info("Nothing changed.")
            else:
                result = api.update_global_settings(changes)
                if result.get("success"):
                    _flash("Saved. Applies to every course from the next question.", "success", "tuning_global")
                    st.rerun()
                else:
                    st.error(result.get("error") or "Could not save these settings.")
        _show_flashes("tuning_global")


def render_settings_page():
    """T8-09 — the screen for T8-08's live configuration.

    Nothing here needs a restart: the backend resolves settings per request, so
    a change is in effect for the next question asked. That matters because a
    restart on this host logs everyone out and drops the model out of VRAM,
    which is a 40-second wait for whoever asks next.
    """
    st.markdown("### ⚙️ Tuning")
    st.caption(
        "Retrieval and answering settings, applied without restarting anything. "
        "Changes take effect on the next question."
    )

    user = st.session_state.get("user") or {}
    role = user.get("role", "Student")
    styles_payload = api.get_response_styles()
    styles = styles_payload.get("styles") or []

    manageable = [c for c in _all_courses() if c.get("can_manage")]

    if role == "Admin":
        tab_course, tab_global = st.tabs(["Per course", "Global"])
    else:
        tab_course, tab_global = st.container(), None

    with tab_course:
        if not manageable:
            st.info(
                "You do not own any courses yet, so there is nothing to tune here. "
                "Courses you create are yours to configure; ask an admin to hand "
                "over one that already exists."
            )
        else:
            codes = [c.get("course_code") for c in manageable]
            # Open on the course the rest of the session is scoped to. Opening
            # on whichever course sorts first invites editing one course's
            # retrieval settings while reading another course's answers, and
            # nothing on the screen would say so.
            scoped = st.session_state.get("course_id")
            picked = st.selectbox(
                "Course", codes,
                index=codes.index(scoped) if scoped in codes else 0,
                format_func=lambda code: _course_display_label(code),
                key="tuning_course",
            )
            if picked:
                _render_course_tuning(picked, styles, styles_payload.get("default"))

    if tab_global is not None:
        with tab_global:
            _render_global_tuning(styles)


# ─── ADMIN DASHBOARD (Admin only) ──────────────────────────────────

def render_courses_page():
    """T05 — Card-based course browser, backed by real /api/courses data.
    T8-05 — Students can now see all available courses and join unenrolled ones.
    """
    st.markdown("### 📚 My Courses")
    st.caption("Select a course to scope your Q&A queries, uploads, and document retrieval.")

    user = st.session_state.get("user") or {}
    role = user.get("role", "Student")
    # Only a student can join a course (the API refuses everyone else), so
    # nobody else is offered a Join button.
    is_student = str(role).lower() == "student"
    active_cid = st.session_state.get("course_id")
    courses = _all_courses()

    if not courses:
        st.info("No courses available — the backend may be offline.")
        return

    enrolled_codes = set(_course_options_for_user(user))
    enrolled = [c for c in courses if c.get("course_code") in enrolled_codes]
    available = [c for c in courses if c.get("course_code") not in enrolled_codes
                 and c.get("is_active", True)]

    # ── Enrolled courses ──
    if enrolled:
        st.markdown("#### Your Courses")
        cols = st.columns(2, gap="medium")
        for idx, course in enumerate(enrolled):
            code = course.get("course_code", "?")
            is_active = code == active_cid
            with cols[idx % 2]:
                border_style = "border-left: 4px solid #0D9488;" if is_active else "border-left: 4px solid #E2E8F0;"
                bg = "#F0FDFA" if is_active else "#FFFFFF"
                with st.container(border=True):
                    st.markdown(
                        f"<div style='{border_style} padding-left: 12px; background: {bg}; border-radius: 4px;'>"
                        f"<span style='font-size:1.1rem; font-weight:700; color:#1B2A4A;'>{'✅ ' if is_active else ''}{_html.escape(code)}</span><br/>"
                        f"<span style='font-size:0.85rem; color:#475569;'>{_html.escape(course.get('name', ''))}</span><br/>"
                        f"<span style='font-size:0.78rem; color:#64748B;'>{_html.escape(course.get('description', '') or 'No description.')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    members = api.get_course_members(code) if role == "Admin" else []
                    docs = api.get_documents(code)
                    stats_parts = [f"📄 {len(docs)} docs"]
                    if members:
                        stats_parts.append(f"👥 {len(members)} members")
                    active_label = "🟢 Active" if course.get("is_active", True) else "⚪ Inactive"
                    stats_parts.append(active_label)
                    st.caption(" · ".join(stats_parts))

                    if is_active:
                        st.button("✓ Active Course", key=f"sel_{code}", type="primary",
                                  use_container_width=True, disabled=True)
                    else:
                        if st.button(f"Switch to {code}", key=f"sel_{code}", use_container_width=True):
                            st.session_state.course_id = code
                            st.session_state.selected_course_id = code
                            st.rerun()

                    # Leaving has worked in the API and the client since
                    # self-enrolment shipped, but no control ever called it, so
                    # a student could join a course and never get back out.
                    # Confirmed in two steps because one stray click would drop
                    # their access to the materials.
                    if str(role).lower() == "student":
                        if st.session_state.get("confirm_leave") == code:
                            st.warning(f"Leave {code}? You will lose access to its materials.")
                            yes_col, no_col = st.columns(2)
                            if yes_col.button("Yes, leave", key=f"leave_yes_{code}",
                                              use_container_width=True):
                                result = api.leave_course(code)
                                st.session_state.confirm_leave = None
                                if result.get("success"):
                                    if result.get("enrolled_courses") is not None:
                                        st.session_state.user["enrolled_courses"] = result["enrolled_courses"]
                                    _refresh_course_options()
                                    # Never leave the chat pointed at a course
                                    # the student can no longer query.
                                    if st.session_state.get("course_id") == code:
                                        left = _course_options_for_user(st.session_state.user)
                                        st.session_state.course_id = left[0] if left else None
                                        st.session_state.selected_course_id = st.session_state.course_id
                                    _flash(f"Left {code}.")
                                    st.rerun()
                                else:
                                    st.error(result.get("error", "Could not leave this course."))
                            if no_col.button("Cancel", key=f"leave_no_{code}",
                                             use_container_width=True):
                                st.session_state.confirm_leave = None
                                st.rerun()
                        elif st.button(f"Leave {code}", key=f"leave_{code}",
                                       use_container_width=True):
                            st.session_state.confirm_leave = code
                            st.rerun()
    else:
        if is_student:
            st.info("You are not enrolled in any course yet.")
        elif str(role).lower() == "admin":
            st.info("There are no active courses yet. Create or reactivate one in the Admin Dashboard.")
        else:
            st.info("You are not assigned to any course yet.")

    # ── Available courses to join (T8-05) ──
    if available:
        st.divider()
        st.markdown("#### Available Courses")
        st.caption("Join a course to start asking questions about its materials." if is_student
                   else _STAFF_COURSE_HINT)
        cols2 = st.columns(2, gap="medium")
        for idx, course in enumerate(available):
            code = course.get("course_code", "?")
            with cols2[idx % 2]:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='border-left: 4px solid #D4A843; padding-left: 12px; border-radius: 4px;'>"
                        f"<span style='font-size:1.1rem; font-weight:700; color:#1B2A4A;'>{_html.escape(code)}</span><br/>"
                        f"<span style='font-size:0.85rem; color:#475569;'>{_html.escape(course.get('name', ''))}</span><br/>"
                        f"<span style='font-size:0.78rem; color:#64748B;'>{_html.escape(course.get('description', '') or 'No description.')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    # Materials are private until the user joins this course.
                    st.caption("🟢 Active · Join to access course materials" if is_student
                               else "🟢 Active")

                    if is_student and st.button(f"Join {code}", key=f"join_{code}", type="primary",
                                                use_container_width=True):
                        result = api.join_course(code)
                        if result.get("success"):
                            if result.get("enrolled_courses") is not None:
                                st.session_state.user["enrolled_courses"] = result["enrolled_courses"]
                            _refresh_course_options()
                            # The first course a student joins becomes the
                            # active one, so the chat page has something to
                            # resolve to rather than reopening on nothing.
                            if not st.session_state.get("course_id"):
                                st.session_state.course_id = code
                                st.session_state.selected_course_id = code
                            _flash(f"Enrolled in {code}!")
                            st.rerun()
                        else:
                            st.error(result.get("error", "Enrolment failed."))

    st.divider()
    if active_cid:
        st.info(f"Your questions and materials are scoped to **{_course_display_label(active_cid)}**.")


# Column shares for the member list: User, Email, Role, Remove. The last column
# used to take 1 share in 9, so the word "Remove" broke into "Remov / e" at any
# window width. At a 900 px window the content area leaves about 430 px for the
# row, and the button needs about 90 of them, so a test keeps the last column
# above 20% of the row. The "Enrol" row below follows the same rule.
_MEMBER_ROW_RATIO = [2.8, 2.7, 1.7, 2.1]
_ADD_MEMBER_RATIO = [2.6, 1.8, 1.4]


def render_course_management():
    """T05 — Courses & enrollments, backed by /api/courses (Sprint 7 T03).

    Uses st.container(border=True) instead of st.expander throughout — the
    expander's arrow icon relies on a web font that doesn't load in some
    environments and renders as literal overlapping text instead of a glyph.
    """
    st.markdown("#### Courses & Enrolments")
    st.caption("Live from /api/courses — create courses and manage who's enrolled.")

    with st.container(border=True):
        st.markdown("**➕ Create a new course**")
        with st.form("create_course_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            new_code = c1.text_input("Course code", placeholder="e.g. CSIT330")
            new_name = c2.text_input("Course name", placeholder="e.g. Software Testing")
            new_desc = st.text_area("Description (optional)", height=68)
            if st.form_submit_button("Create course", type="primary"):
                if not new_code.strip() or not new_name.strip():
                    st.error("Course code and name are required.")
                else:
                    result = api.create_course(
                        new_code.strip().upper(), new_name.strip(), new_desc.strip() or None
                    )
                    if result.get("success"):
                        _flash(f"Created {new_code.strip().upper()}.")
                        _refresh_course_options()
                        st.rerun()
                    else:
                        st.error(result.get("error") or "Failed to create course.")

    courses = _all_courses()
    if not courses:
        st.info("No courses yet, or the database backend is unavailable.")
        return

    for course in courses:
        code = course.get("course_code", "?")
        active = course.get("is_active", True)
        status_icon = "🟢" if active else "⚪"
        with st.container(border=True):
            st.markdown(f"**{status_icon} {code} — {course.get('name', '')}**")
            st.caption(course.get("description") or "No description.")

            members = api.get_course_members(code)
            if members:
                mcols = st.columns(_MEMBER_ROW_RATIO)
                for col, header in zip(mcols, ["User", "Email", "Role", ""]):
                    col.markdown(f"**{header}**")
                for m in members:
                    mcols = st.columns(_MEMBER_ROW_RATIO)
                    mcols[0].write(m.get("username", "—"))
                    mcols[1].write(m.get("email", "—"))
                    mcols[2].write(str(m.get("membership_role", "—")).capitalize())
                    if mcols[3].button("Remove", key=f"rm_{code}_{m.get('email')}",
                                       use_container_width=True):
                        result = api.remove_course_member(code, m.get("email", ""))
                        if result.get("success"):
                            st.rerun()
                        else:
                            st.error(result.get("error") or "Failed to remove member.")
            else:
                st.caption("No members enrolled yet.")

            with st.form(f"add_member_form_{code}", clear_on_submit=True):
                a1, a2, a3 = st.columns(_ADD_MEMBER_RATIO)
                add_email = a1.text_input("Email", label_visibility="collapsed",
                                          placeholder="email@example.com")
                add_role = a2.selectbox("Role", ["student", "lecturer"], label_visibility="collapsed")
                if a3.form_submit_button("Enrol"):
                    if not add_email.strip():
                        st.error("Email is required.")
                    else:
                        result = api.add_course_member(code, add_email.strip(), add_role)
                        if result.get("success"):
                            st.rerun()
                        else:
                            st.error(result.get("error") or "Failed to enrol member.")

            if active:
                if st.button("Deactivate course", key=f"deact_{code}"):
                    result = api.deactivate_course(code)
                    if result.get("success"):
                        _refresh_course_options()
                        st.rerun()
                    else:
                        st.error(result.get("error") or "Failed to deactivate course.")
            else:
                # Deactivating used to be a one-way door: the API has always
                # accepted PATCH is_active, but no control ever sent it, so a
                # course switched off by accident stayed off.
                st.caption("Deactivated — students cannot see or join this course.")
                if st.button("Reactivate course", key=f"react_{code}"):
                    result = api.reactivate_course(code)
                    if result.get("success"):
                        _refresh_course_options()
                        st.rerun()
                    else:
                        st.error(result.get("error") or "Failed to reactivate course.")


def render_pending_lecturers() -> None:
    """Lecturer accounts waiting for an administrator's decision.

    A lecturer who signs up cannot sign in until an administrator approves the
    account. Each decision is confirmed first, like deleting a document, and its
    result is checked: a failed save is shown and never reads as done.
    """
    try:
        pending = api.get_pending_users()
    except APIReadError:
        st.warning("Pending lecturer accounts could not be loaded. Please retry.")
        return

    st.markdown(f"#### Pending lecturer accounts ({len(pending)})")
    if not pending:
        st.caption("No accounts are waiting.")
        return
    st.caption("A lecturer who signs up cannot sign in until you approve the account.")

    asking = st.session_state.get("confirm_user_decision")
    for account in pending:
        uid = account.get("user_id")
        requested = _local(account.get("created_at"))
        with st.container(border=True):
            # st.text, not markdown: the name and address are typed by whoever
            # signed up.
            st.text(f"{account.get('username', '—')} · {account.get('email', '—')}")
            st.caption("Requested " + (requested.strftime("%Y-%m-%d %H:%M") if requested else "—"))

            if asking and asking.get("user_id") == uid:
                approve = asking.get("action") == "approve"
                if approve:
                    st.warning("Approve this account? They will be able to sign in as a lecturer.")
                else:
                    st.warning("Reject this account? They will not be able to sign in.")
                yes_col, no_col, _ = st.columns([1.6, 1.3, 3])
                with yes_col:
                    confirmed = st.button("Yes, approve" if approve else "Yes, reject",
                                          key=f"{'approve' if approve else 'reject'}_yes_{uid}",
                                          use_container_width=True)
                with no_col:
                    cancelled = st.button("Cancel", key=f"decision_no_{uid}", use_container_width=True)
                if confirmed:
                    result = api.approve_user(uid) if approve else api.reject_user(uid)
                    st.session_state.confirm_user_decision = None
                    if result.get("success"):
                        st.toast("Account approved." if approve else "Account rejected.")
                        st.rerun()
                    else:
                        st.error(result.get("error") or "Could not save the decision.")
                elif cancelled:
                    st.session_state.confirm_user_decision = None
                    st.rerun()
            else:
                approve_col, reject_col, _ = st.columns([1.3, 1.3, 3.4])
                with approve_col:
                    approve_clicked = st.button("Approve", key=f"approve_{uid}", type="primary",
                                                use_container_width=True)
                with reject_col:
                    reject_clicked = st.button("Reject", key=f"reject_{uid}", use_container_width=True)
                if approve_clicked:
                    st.session_state.confirm_user_decision = {"user_id": uid, "action": "approve"}
                    st.rerun()
                elif reject_clicked:
                    st.session_state.confirm_user_decision = {"user_id": uid, "action": "reject"}
                    st.rerun()


def _warmup_summary(warmup) -> str:
    """One line saying how the model warm-up went, for the Admin Dashboard."""
    w = warmup if isinstance(warmup, dict) else {}
    if w.get("skipped"):
        return "⏸️ Skipped — warm-up is turned off (EDURAG_OLLAMA_WARMUP)"
    status = str(w.get("status") or "unknown").lower()
    detail = str(w.get("error") or "").strip()[:120]
    if status == "ok":
        ms = w.get("elapsed_ms")
        took = f" in {ms / 1000:.1f} s" if isinstance(ms, (int, float)) else ""
        return f"✅ Ready ({w.get('model') or 'model'} loaded{took})"
    if status == "degraded":
        return f"⚠️ Degraded — {detail or 'the test answer did not complete'}"
    if status == "failed":
        return f"❌ Failed — {detail or 'no detail recorded'}"
    if status == "running":
        return "⏳ Running"
    if status == "pending":
        return "⏳ Not started yet"
    return "❔ Unknown"


def render_admin_page():
    st.markdown("### ⚙️ Admin Dashboard")
    st.markdown("<span class='status-badge' style='background:#FEE2E2; color:#991B1B;'>Admin</span>", unsafe_allow_html=True)

    stats = api.get_admin_stats()
    if stats.get("_offline"):
        st.warning(stats.get("error") or "Admin metrics are unavailable. Please retry.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Courses", stats.get("courses", "—"))
        c2.metric("Documents", stats.get("documents", "—"), f"{stats.get('uploaded_documents', 0)} uploaded")
        c3.metric("Indexing jobs", stats.get("indexing_jobs", "—"))
        warmup = stats.get("warmup") or {}
        c4.metric("Backend mode", stats.get("mode", "unknown"))
        c4.caption(f"Model warm-up: {_warmup_summary(warmup)}")
        st.caption("Live document and course metrics. System-wide user and conversation totals are not available here.")

    st.divider()
    render_pending_lecturers()
    st.divider()
    render_course_management()
    st.divider()
    st.markdown("#### User Management")
    st.info("A system-wide user directory is not available here. Manage course membership in Courses & Enrolments above.")
    st.markdown("#### System Settings")
    st.write("Use Tuning to view and save global or course settings.")
    if st.button("Open Tuning", key="admin_open_tuning"):
        st.session_state.current_page = "settings"
        st.rerun()


# ─── MAIN APP ───────────────────────────────────────────────────────

# ─── SESSION PERSISTENCE (T9-14) ──────────────────────────────────

# Streamlit keeps everything in st.session_state, which the browser discards on
# reload - so pressing F5 threw the user back to the login screen with their
# conversations apparently gone. The access token now lives in a cookie on the
# app's own origin instead, and is exchanged for a user through /api/auth/me on
# the next load.
#
# The cookie is readable by scripts on this origin (Streamlit components set
# cookies through the browser, so HttpOnly is not available). That is only
# defensible because the answer, filename and metadata strings rendered into
# this page are HTML-escaped - before that, a poisoned document could have read
# it. The two changes belong together.

_AUTH_COOKIE = "paedia_session"
_AUTH_COOKIE_MAX_AGE = 3600  # matches PAEDIA_ACCESS_TOKEN_TTL


def _cookies():
    """A controller for this script run; None if the component is unavailable.

    Constructed fresh every time on purpose. The controller reads the browser's
    cookies once, in its constructor, and a Streamlit component returns its
    default -- an empty dict -- on the run that mounts it, with the real value
    arriving on the next. Caching the controller in session_state therefore
    froze that first empty snapshot forever, and the cookie was written
    correctly but never read back. The library already caches the cookie dict
    itself in session_state under its own key; the object must not be cached
    on top of that.
    """
    try:
        from streamlit_cookies_controller import CookieController
    except ImportError:
        return None
    try:
        return CookieController()
    except Exception:
        return None


def _remember_session(token: str | None) -> None:
    """Queue the write for a completed render, after the login rerun.

    A fixed expiry is essential: rendering the component again must never
    extend the one-hour cookie lifetime.
    """
    if token:
        st.session_state["_auth_cookie_write"] = (
            token, datetime.now(timezone.utc) + timedelta(seconds=_AUTH_COOKIE_MAX_AGE))


def _flush_auth_cookie() -> None:
    pending = st.session_state.get("_auth_cookie_write")
    if pending is None:
        return
    controller = _cookies()
    if controller is None:
        return
    try:
        token, expires = pending
        if token:
            controller.set(_AUTH_COOKIE, token, expires=expires, same_site="strict")
        else:
            controller.remove(_AUTH_COOKIE)
    except Exception:
        pass  # A browser refusing cookies still permits an in-tab login.


_SESSION_ENDED = "Your session has expired or ended. Please sign in again."


def _forget_session() -> None:
    st.query_params.clear()
    st.session_state["_auth_cookie_write"] = (None, None)


def _end_expired_session() -> None:
    """A 401 that cannot be refreshed: end this tab's login locally.

    A tab restored from the cookie holds only the access token, so once it expires
    every request fails with no way to refresh. Going to the sign-in page in one
    step beats a red error and a lost question. This must not call logout:
    logout revokes the whole token family, which would sign out another tab of the
    same login that can still refresh.
    """
    _forget_session()
    _clear_identity_state()
    st.session_state[_API_CLIENT_KEY] = PaediaAPIClient(APIConfig())
    st.session_state.login_error = _SESSION_ENDED


def _restore_session_from_cookie() -> bool:
    """Sign the user back in from the cookie, if it still resolves to a user.

    Returns True when the session was restored. An expired or revoked token
    gets a 401 from the server, and the stale cookie is dropped rather than
    left to fail again on every load.
    """
    controller = _cookies()
    if controller is None or api.config.use_fixtures:
        return False
    try:
        token = controller.get(_AUTH_COOKIE)
    except Exception:
        return False
    if not token:
        # An empty read on the run that mounts the component is not "no
        # cookie" -- it is "the component has not answered yet". Let the script
        # finish so the component actually renders; it reruns the app itself
        # once the browser sends the cookies back, and the restore succeeds on
        # that pass.
        #
        # Do not "help" this along with st.rerun(): that aborts the run before
        # the component is rendered, while leaving Streamlit's default {} in
        # session_state under the library's key -- after which the library
        # never declares the component again and the cookie is never read.
        return False

    result = api.get_current_user(token)
    if not result.get("success"):
        _forget_session()
        _clear_identity_state()
        st.session_state.login_error = _SESSION_ENDED
        return False

    user = _normalise_user_for_ui(result.get("user", {}))
    st.session_state.jwt_token = token
    st.session_state.user = user
    st.session_state.course_options = _course_options_for_user(user)
    st.session_state.course_id = _default_course_for_user(user)
    st.session_state.selected_course_id = st.session_state.course_id
    st.session_state.authenticated = True
    st.session_state.login_error = None
    _hydrate_sessions_from_server()
    if not st.session_state.sessions:
        create_new_session("Welcome Chat")
    return True


def _render_app():
    if not st.session_state.authenticated and not _restore_session_from_cookie():
        render_login_page()
        return

    if st.session_state.get("history_load_pending"):
        _hydrate_sessions_from_server()
    # Before anything reads it. Every screen below, and the sidebar beside
    # them, then works from the same answer.
    _reconcile_active_course()
    render_sidebar()
    _show_flashes()

    page = st.session_state.current_page
    role = st.session_state.user.get("role", "Student")

    if page == "chat":
        render_chat_page()
    elif page == "courses":
        render_courses_page()
    elif page == "history":
        render_history_page()
    elif page == "uploads":
        render_uploads_page()
    elif page == "doc_manager" and role in ("Lecturer", "Admin"):
        render_doc_manager_page()
    elif page == "settings" and role in ("Lecturer", "Admin"):
        render_settings_page()
    elif page == "admin" and role == "Admin":
        render_admin_page()
    else:
        st.session_state.current_page = "chat"
        st.rerun()
    # Normal completion only (never in a finally: st.rerun() raises, and that must
    # keep the message it just queued). Anything not shown by now is not wanted.
    _forget_flashes()


def main():
    if api.config.use_fixtures:
        st.warning("Demo mode — sample data only. Changes are not saved to the live system.")
    try:
        _render_app()
    except APIReadError as exc:
        if exc.status_code == 401:
            # The server rejected the credential and this tab has no refresh token.
            # Retrying cannot help, so go to the sign-in page rather than show an error.
            _end_expired_session()
            st.rerun()
        st.error(str(exc))
        st.caption("Data could not be loaded. Your current conversation has been kept.")
        if st.button("Retry", key="retry_api_read"):
            st.rerun()
    _flush_auth_cookie()


if __name__ == "__main__":
    main()
