# T5 contribution — Q&A prep, Tung's domain (infra / security / access control)

**For:** Taylor's Task 5 Q&A collection (owner: Taylor, with all component
owners)
**From:** Tung

**Status as of this version:** only what's below the line under "Ready to
use" has actually been verified — run, tested, and confirmed working. T12,
T15, and T16 are drafted but **not yet applied to `develop` and `feature/tung-sprint10`, not yet run,
and not yet checked by anyone** — so they're kept in a separate section
further down, marked as not safe to cite yet. If the professor asks about
something in that section before it's actually verified, the honest answer
is "that's in progress, not confirmed yet" — not the polished answer below
it, which would overclaim.

---

## Ready to use — verified this sprint

**Q: How do you stop one course's documents leaking into another course's
answers?**
A: Every retrieval call is scoped by `course_id` at the vector-search layer,
not filtered afterward. This sprint we confirmed a fix that closed a gap
where an *unscoped* document-list request had been returning every course's
files; it's now scoped to the caller's own enrolments, and the response no
longer includes where a file is stored on disk. Evidence: confirmed in the
current codebase (`src/api/routes/documents.py`,
`test_document_course_boundaries.py`) — this was Taylor's fix, which I
checked as part of my T6/T7 verification.

**Q: What happens if someone tries to trick the system by referencing a
course two different ways?**
A: A course can be addressed by its short code or its internal database ID;
both now resolve to the same course and the same access check, so there's
no second, unguarded path in. If the database is briefly unreachable, the
request fails safely rather than guessing. Evidence: confirmed in
`src/api/db.py` / `src/api/state.py` — also Taylor's fix, checked by me.

**Q: If the demo breaks live, what's the fallback?**
A: A pre-recorded run-through, introduced explicitly as a recording if it's
used — not passed off as live. Andre and Tai own that recording; I built a
readiness script that gives a single pass/fail read on every service plus
whether the actual demo question returns a real, sourced answer — instead
of relying on someone eyeballing four different things separately. Evidence:
`scripts/check_demo_ready.py`, verified this sprint.

**Q: How thoroughly has the demo path itself been tested?**
A: *(honest, current answer — use this, not a rosier one)* Every supporting
service — database, vector store, API, frontend — was verified up and
responding correctly on a live run. The final step, whether the production
language model returns a grounded answer, still needs confirming on the
actual GPU host: my own verification hit a hardware ceiling (an 8GB-RAM
laptop can't load a 12B-parameter model), which is expected and not a
system defect, but it does mean that specific check is still open.

---

## In progress — not yet verified, do not present as done

These are drafted and written, but **not yet applied to `develop` and `feature/tung-sprint10`, not yet
run, and not yet checked** — flagging them here so nobody in Q&A (or the
pitch) accidentally states them as finished:

- **Cross-endpoint permission test matrix** (draft: needs to be applied,
  run against a real Postgres, and reviewed by Andre before it counts as
  done).
- **Container hardening** — non-root user and dropped Linux capabilities
  for the app's own containers (draft: needs to be applied and the stack
  needs to be confirmed still starting cleanly, then reviewed by Tai).
- **Duplicate ChromaDB collection cleanup** — an old collection from a
  Sprint 8 rename identified as safe to remove (draft: this touches live
  data on the GPU host and hasn't been run at all yet — deliberately held
  until after the workshop, reviewed by Taylor when it happens).

If asked "is the system's access control/deployment fully hardened," the
honest answer right now is: **the code fixes already on `develop` (course
scoping, course-identifier resolution) are done and tested; broader
hardening and expanded test coverage are planned but not yet landed.**