# T22/T28 — Independent Zip Verification

**Tasks:** T22 (independently verify zip + README) and T28 (verify submission zip contents)
**Done by:** Thanh Binh Tran, standing in — Tung's regression QA (T13) landed 5-6 Aug, but T22/T28 hadn't started yet with the deadline close, so this covers both directly against the built zip rather than a git clone.
**Zip tested:** `submission/edurag-paedia-a4-42a1018.zip`

## T28 — Zip contents

Extracted the zip fresh into an isolated folder outside the repo and checked:

| Check | Result |
|---|---|
| No `.env`, `.git`, or `materials/` (copyright PDF) | Clean |
| No secrets/API keys/passwords in any tracked file | Clean |
| Required A4 deliverables present (report, RTM, architecture docs, branding guide, README, evidence index) | All present |
| `Team_Contributions/` present, all 6 members | Present |
| Sponsor review docs present (`docs/meetings/sprint5_sponsor_review.docx`, `sprint6_sponsor_review.docx`) | Present |
| Every file link inside the extracted README resolves | No broken links |
| Total size | 7.9 MB |

## T22 — README verification (from the zip, not a git clone)

Followed the README setup path against the extracted zip alone, no `.git` folder present:

1. Copied `.env.example` to `.env`, set non-default ports and an isolated Compose project name to avoid touching the live dev stack.
2. `docker compose up -d --build` — all 5 services came up healthy from the zip contents with no manual fixes.
3. Seeded the corpus and pulled the model per README §19.2.
4. `scripts/check_demo_ready.py` — all PASS after warmup.
5. Full pytest suite inside the container: **118 passed**, 1 expected warning (a test that deliberately exercises the offline-embedder fallback path). Took ~11 minutes in-container — slower than Tung's local run since the container installs the full dependency set (sentence-transformers, torch), but not a defect.
6. Logged in with the documented `student@uow.edu.au` credentials and ran the exact question from README §19.2 — got a grounded answer citing `Week1_RAG_Introduction.pdf` p.2, matching what the README promises.

## Findings and fixes made during this pass

- **README assumed a git clone.** A marker grading from the zip doesn't have `.git` and shouldn't run the clone/checkout steps. Added a one-line note in §5 pointing zip-based markers straight to the `.env` copy step.
- **Fixture inconsistency (minor, doesn't affect the documented demo path):** the login fixture's `enrolled_courses` field returns UUIDs, but course-scoped retrieval everywhere else in the system uses string codes like `CSIT321`. Querying with the UUID from `enrolled_courses` returns a fallback response instead of a grounded answer. The Streamlit UI never hits this — it always queries with the hardcoded course code — but it's a real gap for anyone calling the API directly. This is a symptom of the already-documented known limitation (auth/courses are fixture-backed, not a real database) and is naturally resolved by Sprint 7's T01-T05 work wiring real `courses`/`enrollments` tables.

## Result

Zip and README are ready to submit. No blockers found.
