PAEDIA (EduRAG) — MARKER QUICK-START
CSIT321 Project 37 — Group 19, Aletheia's Zetetes
------------------------------------------------------

This is a plain-text quick reference for testing the prototype.
The full README.md in zip file has everything in detail —
use this file to get running fast, and README.md if something
doesn't match what you see here.

WHAT THIS IS
------------
Paedia is a course Q&A assistant. A lecturer uploads course material,
a student asks a question, and the answer is generated only from that
material with a citation (file, page, similarity score) attached. If
nothing in the material matches closely enough, it says so instead of
guessing.

WHAT YOU NEED
-------------
- Docker Desktop, installed and running
- About 10-15 minutes for first-time setup (mostly image/model downloads)
- No GPU required — the base setup runs on CPU. If a GPU is detected,
  the auto-wrapper script picks a faster model automatically.

SETUP (run from this folder, in order)
---------------------------------------
1. Copy the example environment file:

     Windows (PowerShell):  Copy-Item .env.example .env
     Mac/Linux:              cp .env.example .env

2. Start the stack:

     docker compose up -d --build

3. Pull the language model (first run only):

     docker compose exec ollama ollama pull llama3.2

4. Load the sample course material into the vector database:

     docker compose exec api python -m src.document_processor.ingest_corpus

5. Confirm everything is healthy:

     python scripts/check_demo_ready.py

   You should see PASS on all 5 services. If anything says WARN, wait
   about 15 seconds and run the command again — it usually just means
   the API is still warming up.

HOW TO TEST IT
---------------
Open http://localhost:8501 in a browser.

Demo accounts (auth is fixture-based, not a real login system — see
KNOWN LIMITATIONS below):

  Student:  student@uow.edu.au  / student123
  Lecturer: lecturer@uow.edu.au / lecturer123
  Admin:    admin@uow.edu.au    / admin123

Suggested test flow:

  1. Sign in as the student. Ask: "What is Retrieval-Augmented
     Generation?" Expect an answer citing Week1_RAG_Introduction.pdf,
     with a confidence score and model name shown.
  2. Sign out, sign in as the lecturer. Open Document Manager, upload
     any short PDF. Watch it move from queued -> processing -> indexed.
  3. Ask a question that depends on that file — the citation should
     point at the file you just uploaded, with no restart needed.
  4. Sign in as admin to see the system-wide view.

A first query can take up to a couple of minutes on CPU-only hardware
— this is expected, not a hang. Subsequent queries are faster once the
model is warm.

KNOWN LIMITATIONS (stated here, not hidden)
--------------------------------------------
- Auth, courses, and chat sessions are fixture/in-memory, not backed
  by a real database. Only uploaded-document metadata is actually
  persisted to PostgreSQL.
- Retrieval accuracy hasn't been formally benchmarked against a
  labelled query set yet — what's measured so far is generation
  quality and speed.
- The admin dashboard is read-only; user-management actions are
  disabled in this build.

None of these block the core flow above (upload -> index -> ask ->
grounded answer with citations), which is fully live end to end.

IF SOMETHING GOES WRONG
-------------------------
- "docker compose up" fails with a port already in use:
    Edit .env and change the conflicting PORT value, then retry.
- Ollama returns "[Ollama not running]" in the chat:
    docker compose restart ollama
- Getting generic answers instead of cited ones:
    Re-run step 4 above (the corpus may not have been seeded).
Full troubleshooting section: README.md, section 12.

MORE DETAIL
------------
- Everything about the system, requirement-by-requirement: docs/rtm_a4.md
- Architecture and design decisions: docs/a4_report.docx
- Full setup, options, and troubleshooting: README.md
