# UI State Management Design

**Paedia — AI-Powered Course Assistant**
CSIT321 Project 37 · Group 19 — Aletheia's Zetetes
Author: Anmoldeep Singh (8443580)
Date: April 2026

---

## 1. Overview

This document describes how Streamlit's `st.session_state` is used to manage application state across user interactions. Since Streamlit re-runs the entire script on every interaction, all mutable state must be stored in session state to persist between reruns.

Paedia's UI manages four key state domains: **authentication**, **conversation context**, **upload progress**, and **navigation**. These domains map directly to the PostgreSQL relational schema and the four-module architecture defined in the Assessment 2 specification.

### Relationship to System Architecture

The Streamlit prototype UI sits behind the Flask-based WebApplication layer (Module 4), which is the only externally exposed module. The UI communicates with three backend modules through the WebApplication REST API:

- **Module 1: DocumentProcessor** — document upload, parsing (PDF/PPTX/DOCX), chunking (~500 tokens, 50-token overlap), embedding via SentenceTransformers all-MiniLM-L6-v2
- **Module 2: VectorRetriever** — cosine similarity search in ChromaDB, scoped by course_id, returns top-k=5 chunks
- **Module 3: LLMResponseGeneration** — context-grounded prompt construction, LLM call (Ollama dev / OpenAI demo), source citation attachment, fallback labelling
- **Module 4: WebApplication** — Flask service layer, JWT authentication, RBAC, rate limiting, audit logging, session management via PostgreSQL JSONB

---

## 2. Architecture

```
┌───────────────────────────────────────────────────────┐
│                   Streamlit App                        │
│                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────┐ │
│  │  Auth State   │   │  Chat State  │   │ Nav State │ │
│  │              │   │              │   │           │ │
│  │ • jwt_token  │   │ • messages   │   │ • page    │ │
│  │ • user       │   │ • session_id │   │ • params  │ │
│  │ • role       │   │ • course_id  │   │           │ │
│  └──────┬───────┘   └──────┬───────┘   └─────┬─────┘ │
│         │                  │                  │       │
│         └──────────────────┼──────────────────┘       │
│                            │                          │
│                 ┌──────────▼──────────┐               │
│                 │  st.session_state   │               │
│                 │  (central store)    │               │
│                 └────────────────────-┘               │
│                            │                          │
│  ┌──────────────┐   ┌─────▼────────┐                 │
│  │ Upload State  │   │  Flask       │                 │
│  │              │   │  WebApp API  │                 │
│  │ • files      │   │              │                 │
│  │ • progress   │   │ • /api/auth  │                 │
│  │ • indexing   │   │ • /api/query │                 │
│  └──────────────┘   │ • /api/docs  │                 │
│                     └──────────────┘                 │
└───────────────────────────────────────────────────────┘
          │                    │                   │
    ┌─────▼─────┐     ┌───────▼───────┐    ┌──────▼──────┐
    │PostgreSQL │     │   ChromaDB    │    │   Ollama /  │
    │Users,     │     │  course_id    │    │   OpenAI    │
    │Sessions,  │     │  scoped       │    │   LLM       │
    │Audit      │     │  embeddings   │    │             │
    └───────────┘     └───────────────┘    └─────────────┘
```

---

## 3. State Domains

### 3.1 Authentication State

Manages user identity and access control via JWT tokens issued by the Flask WebApplication layer.

| Key | Type | Default | Maps to (PostgreSQL) |
|-----|------|---------|---------------------|
| `authenticated` | `bool` | `False` | — |
| `jwt_token` | `str \| None` | `None` | RefreshToken table |
| `user` | `dict` | `{}` | User table |
| `login_error` | `str \| None` | `None` | — |

**User schema (from PostgreSQL User table):**

```python
{
    "user_id": "uuid",          # User.user_id (UUID PK)
    "username": "str",          # User.username (VARCHAR UNIQUE)
    "email": "str",             # User.email (VARCHAR UNIQUE)
    "role": "str",              # User.role (ENUM: student/lecturer/admin)
    "last_login_at": "str"      # User.last_login_at (TIMESTAMP)
}
```

**Flow:**

```
Login form submit
  → POST /api/auth/login { email, password }
  → Flask validates against User.password_hash (bcrypt)
  → On success: issue JWT + RefreshToken, set authenticated=True
  → On failure: set login_error message
  → On token expiry: use RefreshToken to obtain new JWT
  → On refresh failure: reset authenticated=False, redirect to login
  → All auth events written to AuditLog table
```

**Role-based access (RBAC with 3 roles):**

The `user.role` field controls which pages and features are visible:

- **Student**: Q&A Chat (query only), Session History, My Uploads (read-only docs list)
- **Lecturer**: All student pages + Document Manager (upload/delete, scoped to enrolled courses)
- **Admin**: All pages + Admin Dashboard (user management, system settings, audit log review)

### 3.2 Conversation Context

Manages the active Q&A chat session. Maps to the PostgreSQL Session and Message tables.

| Key | Type | Default | Maps to (PostgreSQL) |
|-----|------|---------|---------------------|
| `messages` | `list[dict]` | `[]` | Message table |
| `session_id` | `str \| None` | `None` | Session.session_id (UUID) |
| `course_id` | `str \| None` | `None` | Session.course_id (FK → Course) |
| `is_loading` | `bool` | `False` | — |
| `last_input` | `str` | `""` | — |

**Message schema (from PostgreSQL Message table):**

```python
{
    "message_id": "uuid",       # Message.message_id (UUID PK)
    "session_id": "uuid",       # Message.session_id (FK → Session)
    "role": "user" | "assistant",  # Message.role (ENUM)
    "content": str,             # Message.content (TEXT)
    "source_references": [      # Message.source_references (JSONB, assistant only)
        {
            "chunk_id": str,        # Chunk.chunk_id (UUID)
            "document_id": str,     # Chunk.document_id (FK → Document)
            "filename": str,        # Document.filename
            "page_number": int,     # Chunk.page_number
            "chunk_order": int,     # Chunk.chunk_order
            "similarity": float     # Cosine similarity score (0.0–1.0)
        }
    ],
    "model_used": str | None,   # Message.model_used (VARCHAR, e.g. "ollama/llama3")
    "token_count": int | None,  # Message.token_count (INT)
    "is_fallback": bool,        # True when no chunks exceed similarity threshold
    "created_at": str           # Message.created_at (TIMESTAMP)
}
```

**Flow:**

```
User submits query (with active course_id)
  → Append user message to messages[]
  → Set is_loading = True
  → POST /api/query { query, session_id, course_id }
  → WebApplication validates JWT, checks rate limit
  → VectorRetriever embeds query with all-MiniLM-L6-v2
  → ChromaDB cosine similarity search (top-k=5, filtered by course_id)
  → LLMResponseGeneration builds context-grounded prompt
  → LLM generates answer (Ollama dev / OpenAI demo)
  → If no chunks exceed threshold: prepend fallback label
  → Receive { answer, source_references[], confidence, model_used, token_count, is_fallback }
  → Append assistant message to messages[]
  → Set is_loading = False
  → Interaction stored in PostgreSQL (Message + AuditLog)
  → Rerun to update UI
```

### 3.3 Upload Progress & Document State

Manages file uploads and indexing status. Maps to the PostgreSQL Document, Chunk, and IndexingJob tables.

| Key | Type | Default | Maps to (PostgreSQL) |
|-----|------|---------|---------------------|
| `documents` | `list[dict]` | `[]` | Document table |
| `upload_queue` | `list[dict]` | `[]` | — |
| `upload_progress` | `dict` | `{}` | IndexingJob.progress_percent |
| `indexing_status` | `dict` | `{}` | IndexingJob.status |

**Document schema (from PostgreSQL Document table):**

```python
{
    "document_id": "uuid",      # Document.document_id (UUID PK)
    "course_id": "uuid",        # Document.course_id (FK → Course)
    "uploaded_by": "uuid",      # Document.uploaded_by (FK → User)
    "filename": str,            # Document.filename (VARCHAR)
    "file_type": str,           # Document.file_type (VARCHAR, e.g. "application/pdf")
    "file_size_bytes": int,     # Document.file_size_bytes (BIGINT)
    "page_count": int,          # Document.page_count (INT)
    "storage_path": str,        # Document.storage_path (VARCHAR)
    "status": str,              # Document.status (ENUM: pending/processing/indexed/failed)
    "uploaded_at": str          # Document.uploaded_at (TIMESTAMP)
}
```

**Upload flow (via Module 1: DocumentProcessor):**

```
File selected via st.file_uploader (PDF, PPTX, or DOCX only)
  → Validate file type and size
  → POST /api/documents/upload (multipart) with course_id
  → Flask creates Document record (status: "pending")
  → Flask creates IndexingJob record (status: "queued")
  → DocumentProcessor parses file with format-specific parser
  → Text split into chunks (~500 tokens, 50-token overlap)
  → SentenceTransformers all-MiniLM-L6-v2 generates 384-dim embeddings
  → Embeddings written to ChromaDB with course_id metadata
  → Document.status updated: "pending" → "processing" → "indexed"
  → IndexingJob.progress_percent updated (0 → 100)
  → On failure: Document.status = "failed", IndexingJob.error_message set
  → AuditLog entry written for upload event
```

**Polling strategy:**

Since Streamlit doesn't support WebSockets natively, we use `st.empty()` + `time.sleep()` for upload progress polling. For production, consider:
- Streamlit's `st_autorefresh` component for periodic polling
- A callback-based approach using `st.experimental_fragment` (Streamlit ≥ 1.33)

### 3.4 Navigation State

Manages page routing and UI configuration.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `current_page` | `str` | `"chat"` | Active page: chat, history, uploads, documents, admin |
| `sidebar_expanded` | `bool` | `True` | Sidebar visibility |
| `active_course` | `str \| None` | `None` | Selected course_id for scoping queries and uploads |
| `dark_mode` | `bool` | `False` | Theme toggle (stretch goal) |

**Navigation flow:**

```
Sidebar button clicked
  → Set current_page = target
  → st.rerun() triggers full re-render
  → Main function reads current_page, renders correct component
  → Role check: if page requires lecturer/admin, verify user.role
```

---

## 4. Initialization Pattern

All state is initialized at app startup using a defaults dictionary. This pattern ensures state is only set once per session, not on every rerun:

```python
def init_session_state():
    defaults = {
        # Auth (maps to User + RefreshToken tables)
        "authenticated": False,
        "jwt_token": None,
        "user": {},
        "login_error": None,
        # Conversation (maps to Session + Message tables)
        "messages": [],
        "session_id": None,
        "course_id": None,
        "is_loading": False,
        "last_input": "",
        # Documents (maps to Document + IndexingJob tables)
        "documents": [],
        "upload_queue": [],
        "upload_progress": {},
        "indexing_status": {},
        # Navigation
        "current_page": "chat",
        "active_course": None,
        "dark_mode": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
```

This is called once at the top of the script. The `if key not in st.session_state` guard prevents overwriting state on reruns.

---

## 5. State Transitions Diagram

```
                    ┌─────────────┐
                    │   STARTUP   │
                    └──────┬──────┘
                           │
                    init_session_state()
                           │
                    ┌──────▼──────┐
               ┌────│    LOGIN    │
               │    └──────┬──────┘
          auth fails       │ JWT issued
               │    ┌──────▼──────┐
               └───►│    CHAT     │◄──── default landing
                    │ (course_id  │      (student view)
                    │  scoped)    │
                    └──┬───┬───┬──┘
                       │   │   │
            ┌──────────┘   │   └──────────┐
            ▼              ▼              ▼
     ┌───────────┐  ┌───────────┐  ┌───────────┐
     │  HISTORY  │  │  UPLOADS  │  │   ADMIN   │
     │ (Session  │  │ (Document │  │ (AuditLog │
     │  table)   │  │  table)   │  │  + User)  │
     └───────────┘  └─────┬─────┘  └───────────┘
                          │        (role: admin only)
                    ┌─────▼─────┐
                    │  DOC MGR  │
                    │ (Lecturer │
                    │  + Admin) │
                    └───────────┘
```

---

## 6. PostgreSQL Schema Reference

The UI state maps to the following PostgreSQL tables (see Assessment 2 ER diagram, Figure 4):

| UI State Domain | PostgreSQL Tables | ChromaDB |
|----------------|-------------------|----------|
| Authentication | User, RefreshToken, AuditLog | — |
| Conversation | Session, Message | — |
| Documents | Document, Chunk, IndexingJob | course_id-scoped embeddings |
| Navigation | Course, UserCourseEnrollment | — |

Key relationships:
- `User` → `Session` (1:N) — each user can have multiple chat sessions
- `Session` → `Message` (1:N) — each session contains ordered messages
- `Course` → `Document` (1:N) — documents scoped to a course
- `Document` → `Chunk` (1:N) — each document split into indexed chunks
- `Chunk` embeddings stored in ChromaDB, not PostgreSQL (separation of relational and vector state)

---

## 7. React Migration Notes (Stretch Goal)

If the project moves to a React frontend with FastAPI, the state model maps directly:

| Streamlit | React Equivalent |
|-----------|-----------------|
| `st.session_state` | React Context + `useReducer` |
| `st.rerun()` | State update triggers re-render |
| `st.cache_data` | `useMemo` / React Query |
| Sidebar navigation | React Router |
| `st.file_uploader` | `react-dropzone` + upload hooks |
| Flask WebApplication | FastAPI (same REST endpoints) |

The state schema (messages, documents, auth) remains identical — only the rendering layer changes. The PostgreSQL and ChromaDB schemas are untouched.

---

## 8. Error Handling

| Scenario | State Change | User Feedback |
|----------|-------------|---------------|
| Network timeout | `is_loading = False` | Toast: "Connection lost, retrying..." |
| JWT expired | attempt refresh via RefreshToken | Silent refresh; redirect to login on failure |
| Upload too large | Remove from queue | Inline error below uploader |
| Invalid file type | Reject (only PDF/PPTX/DOCX) | Inline error: "Unsupported format" |
| Indexing failure | `doc.status = "failed"` | Red badge + retry button in table |
| LLM rate limit | `is_loading = False` | Message: "Please wait and try again" |
| No relevant chunks | `is_fallback = True` | Yellow-bordered message with fallback label |

---

## 9. Security Considerations

- **JWT authentication**: Stateless tokens issued by Flask WebApplication. Access tokens are short-lived; refresh tokens stored in PostgreSQL RefreshToken table with revocation support.
- **Token storage**: Auth tokens are stored in `st.session_state`, which lives server-side in Streamlit's session memory. Tokens are never exposed to the client browser.
- **Role checks (RBAC)**: Every page render checks `user.role` before displaying admin/lecturer features. Three roles: Student (query only), Lecturer (upload + content management), Admin (system configuration + user management).
- **Input sanitisation**: User queries are sanitised before sending to the backend. Prompt templates enforce course-scoping and citation rules in highest-priority system instructions (per OWASP LLM01:2025 guidance).
- **Session expiry**: Sessions auto-expire after 30 minutes of inactivity (configurable in Streamlit config).
- **Audit logging**: All significant events (login, query, upload, admin actions) are written to the AuditLog table with user_id, event_type, event_data (JSONB), and ip_address.
