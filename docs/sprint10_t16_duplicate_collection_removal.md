# T16 — Remove the duplicate vector collection

**Task:** T16 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Taylor
**Sprint:** 10
**Status:** Deletion already done live on 24 Sept 2026 (confirmed by Taylor's
27 Sept review of PR #134, point 5). No step-by-step terminal output was
captured at the time it happened — this doc was only written up afterward.
Sections 1–4 below are therefore **not** a record of what happened; they're
what's known, what isn't, and the plan to get real current-state evidence
without needing local storage, a GPU, or reproducing the deletion.

**The helper script `scripts/cleanup_duplicate_collection.py` has been
removed** (Taylor's review of #136: the work is done, this doc is the record).
It only ever did three things — list collections with chunk counts, delete a
named non-active collection after a backup, and run one test retrieval — and
Section 2 below does the two read-only ones with plain one-liners.

**Background:** `src/document_processor/ingest_corpus.py` documents its own
history — the collection was renamed `csit321_course` -> `edurag_course`
(the `COLLECTION` constant) in Sprint 8 (T8-13), when the corpus grew to
hold four subjects. Nothing in the codebase references `csit321_course` any
more (`grep -rn "csit321_course" src/ apps/ scripts/` returns nothing), so it
was orphaned data from that rename, not something anything still read.

---

## 1. What's known to be true, and what isn't

| Claim | Status |
|-------|--------|
| `csit321_course` no longer exists on the live host | Confirmed — Taylor's 27 Sept review states it was deleted on 24/9 |
| A volume backup was taken before deleting it | **Not documented here.** Worth confirming directly with whoever ran it, or checking the host for a `chromadb_backup_*.tar.gz` file, rather than assuming |
| The query path still returns grounded answers after the deletion | **Not verified with saved output.** Section 2 below is how to get real evidence of this now, four days later — which also confirms the deletion didn't quietly regress anything since |

Don't mark this PASS in Section 5 until at least the second row above has an
answer. A task can be genuinely done and still be missing the evidence T18's
requirements inventory needs to point at — those are two different problems,
and only the second one is what this doc exists to fix.

---

## 2. Getting real, current output — no local GPU or storage needed

Both checks below need the packages and network access the running `api`
container already has (ChromaDB client, `sentence-transformers`), so they run
*inside that container* — whoever has SSH or Tailscale access to the host
needs only a terminal, no local install, GPU or storage. Both are read-only.

```powershell
docker compose exec api python -c "from src.document_processor.ingest_corpus import get_chroma_client, COLLECTION; c=get_chroma_client(); [print(getattr(x,'name',x), c.get_collection(getattr(x,'name',x)).count()) for x in c.list_collections()]; print('active collection:', COLLECTION)"
```
<PASTE FULL OUTPUT — should list only `edurag_course`, with
`csit321_course` absent>

```
<paste here>
```

```powershell
docker compose exec api python -c "from src.document_processor.rag_pipeline import VectorRetriever; r=VectorRetriever().search('What is retrieval-augmented generation?', course_id='CSIT321', top_k=3); print(len(r), 'chunks'); [print(x.source_file, x.page_number, round(x.similarity,4)) for x in r]"
```
<PASTE FULL OUTPUT — should show real chunks with source files and
similarity scores, not zero results>

```
<paste here>
```

(These one-liners reuse the calls the removed script made; they have not been
run against the live host yet — if one errors on a name, that is the first
thing to fix, not a sign the deletion went wrong.)

If you don't personally have host access, this is the one step in this doc
that genuinely needs someone else (whoever ran the original deletion, or
Taylor/Andre/Tai if they have it) — flag it to them directly rather than
leaving it unasked, since two copy-pasted commands is a small favour to
request against "the evidence T18 needs is missing."

---

## 3. The backup — confirm it exists, don't try to recreate it

There's nothing to delete anymore, so there's no version of Section 1 from
the original template to re-run. What's still worth doing is confirming the
backup itself is real and not just assumed:

```powershell
# On the host, wherever backups are kept:
Get-Item .\chromadb_backup_*.tar.gz | Select Name, Length
```
<PASTE — filename, size, and where it's stored (not the same host you'd be
restoring to, if it ever came to that)>

```
<paste here>
```

If no such file turns up anywhere, say so plainly in Section 5 rather than
leaving it implied — "collection deleted, backup status unconfirmed" is a
true and useful thing for Taylor to know before sign-off, and a false PASS
here is worse than an honest partial one.

---

## 4. Manual check (optional, but cheap corroboration)

Ask a real question through the Streamlit UI for a course that was indexed
(e.g. CSIT321) and confirm the answer still cites real sources. Anyone with
access to the live Streamlit UI can do this in under a minute — it doesn't
require the host terminal access Section 2 does.

Manual check result: <PASS/FAIL — describe>

---

## 5. Result

**Overall Result:** <fill in once Section 2's output exists — don't mark
PASS from Taylor's review comment alone; that confirms the deletion
happened, not that the done-when condition (backup exists, retrieval still
grounded) is evidenced>

**Backup location:** <fill in from Section 3, or "unconfirmed" if nothing
turns up>

---

## 6. Sign-off

- [x] Helper script removed from the repo (this doc is the record)
- [ ] This file is a finalised file with real, current command output (Section 2)
- [ ] Backup existence confirmed, not assumed (Section 3)
- [x] Deletion itself confirmed done (24 Sept 2026, per Taylor's 27 Sept review)
- [x] This file committed to `feature/tung-sprint10` and pushed