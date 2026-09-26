# T16 — Remove the duplicate vector collection

**Task:** T16 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Taylor
**Sprint:** 10 
**Noted:** This is the draft file that haven't running test yet

**Definition of Done** (from the sprint plan)
> The collection is gone, a backup exists, and a question still returns a
> properly grounded answer.

**Branch Tested**

```
feature/tung-sprint10
```

**Background:** `src/document_processor/ingest_corpus.py` documents its own
history — the collection was renamed `csit321_course` -> `edurag_course`
(the `COLLECTION` constant) in Sprint 8 (T8-13), when the corpus grew to
hold four subjects. Nothing in the codebase references `csit321_course` any
more (`grep -rn "csit321_course" src/ apps/ scripts/` returns nothing), so
it is orphaned data from that rename, not something anything still reads.

This must be run **against the live GPU host's ChromaDB**, not a local dev
instance — the duplicate the sprint plan describes (~2,200 passages) is host
state, not something in a fresh checkout.

---

## 1. Backup — do this before anything else

```powershell
# On the GPU host (or via Tailscale if docker compose is reachable remotely):
docker compose exec chromadb sh -c "tar -C /data -czf /tmp/chromadb_backup_$(Get-Date -Format yyyyMMdd_HHmm).tar.gz ."
docker cp <chromadb_container_name>:/tmp/chromadb_backup_<timestamp>.tar.gz .\chromadb_backup_<timestamp>.tar.gz
```

Confirm the archive exists and is non-trivially sized before continuing:

```powershell
Get-Item .\chromadb_backup_*.tar.gz | Select Name, Length
```

<PASTE the filename and size here>

```
<paste here>
```

---

## 2. List collections

```powershell
python scripts/cleanup_duplicate_collection.py --list
```

<PASTE FULL OUTPUT — should show both `edurag_course` (marked as the active
COLLECTION) and `csit321_course` with its chunk count>

```
<paste here>
```

**Chunk count found in `csit321_course`:** <fill in>
**Matches the ~2,200 the sprint plan estimated?** <yes/no — if wildly
different, stop and check you're pointed at the right host before deleting
anything>

---

## 3. Dry run

```powershell
python scripts/cleanup_duplicate_collection.py --target csit321_course --dry-run
```

<PASTE OUTPUT — sample chunks it would remove>

```
<paste here>
```

---

## 4. Delete (only after Section 1's backup exists)

```powershell
python scripts/cleanup_duplicate_collection.py --target csit321_course --confirm-delete
```
Type `yes` at the confirmation prompt only once you've checked the box
below.

- [ ] Backup from Section 1 confirmed to exist and be non-empty.

<PASTE OUTPUT>

```
<paste here>
```

---

## 5. Verify — through the query path, a different component from the one that deleted it

```powershell
python scripts/cleanup_duplicate_collection.py --verify
```

<PASTE OUTPUT — should show real chunks returned with source files and
similarity scores, not an empty result>

```
<paste here>
```

Also confirm manually: ask a real question through the Streamlit UI for a
course that was indexed (e.g. CSIT321) and check the answer still cites real
sources.

Manual check result: <PASS/FAIL — describe>

---

## 6. Re-list to confirm removal

```powershell
python scripts/cleanup_duplicate_collection.py --list
```

<PASTE — `csit321_course` should no longer appear>

```
<paste here>
```

---

## 7. Result

**Overall Result:** <PASS / FAIL>

**Backup location (for Taylor's sign-off):** <path/filename, and where it's
stored — don't leave the only copy on the same host you just modified>

---

## 8. Sign-off

- [] This file is a finalised file with a fully running test
- [x] This file committed to `feature/tung-sprint10` and pushed