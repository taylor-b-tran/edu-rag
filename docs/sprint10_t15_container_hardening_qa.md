# T15 — Container hardening

**Task:** T15 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Tai
**Sprint:** 10 
**Noted:** This is the draft file that haven't running test yet

**Definition of Done** (from the sprint plan)
> Each service runs with reduced privileges and the stack still starts
> cleanly from scratch.

**Branch Tested**

```
feature/tung-sprint10
```

---

## 0. What changed

| Service | Before | After |
|---------|--------|-------|
| `api` | root, all default capabilities, no privilege-escalation guard | non-root `edurag` user (uid 10001, baked into `docker/Dockerfile.demo`), `cap_drop: [ALL]`, `security_opt: no-new-privileges:true` |
| `streamlit` | same as api | same as api |
| `app` (tools container, `profiles: tools`) | root | stays root deliberately (interactive debug shell, never auto-started, never exposed on a port) — capabilities still dropped |
| `postgres` | root-capable default image | `cap_drop: [ALL]` + `cap_add: [CHOWN, SETUID, SETGID, DAC_OVERRIDE, FOWNER]` (the official entrypoint needs these for first-run `initdb`/chown of `postgres_data`) |
| `chromadb` | root-capable default image | `cap_drop: [ALL]`, no-new-privileges. Left as image-default user pending the verification in Section 3 |
| `ollama` | root-capable default image | `cap_drop: [ALL]`, no-new-privileges. Left root and read-write deliberately — see the comment in `docker-compose.yml` on GPU passthrough risk |

**Not done, and deliberately not attempted this sprint:** a read-only root
filesystem on `api`/`streamlit`. The repo is bind-mounted for hot
development and several write paths (pip cache, gunicorn's own runtime
files) haven't been enumerated yet. Doing this properly needs its own pass —
flagged as follow-up, not silently dropped from scope.

---

## 1. Run Environment

| Field | Value |
|-------|-------|
| Date | <PASTE> |
| Operating System | Windows 11 |
| Docker Desktop Version | <PASTE: docker --version and docker compose version> |
| Test Command | see Section 2 |

---

## 2. Verification steps and exact output to paste back

Run these in order from the repo root, on `feature/tung-sprint10`.

### 2.1 — Config validates

```powershell
docker compose config --quiet
```
A clean exit with no output means the YAML is well-formed and every
variable resolves. Paste whatever it prints (ideally nothing):

```
<paste here>
```

### 2.2 — Full stack builds and starts clean from a cold volume set

**Warning:** this recreates `postgres_data`/`chromadb_data` from empty. Only
run this against your local dev stack, never the shared GPU host.

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps
```

Paste the `docker compose ps` output — every service should show `healthy`
or `running`:

```
<paste here>
```

### 2.3 — Confirm the api/streamlit containers are actually non-root

```powershell
docker compose exec api id
docker compose exec streamlit id
```
Expected: `uid=10001(edurag) gid=10001(edurag)` for both. Paste actual output:

```
<paste here>
```

### 2.4 — Confirm capabilities were actually dropped

```powershell
docker compose exec api sh -c "cat /proc/1/status | grep Cap"
```
`CapEff` should be `0000000000000000` (or very close to it — a couple of
bits may remain from what Docker itself always grants regardless of
`cap_drop`, worth checking if it isn't exactly zero). Paste output:

```
<paste here>
```

### 2.5 — App still works end to end

```powershell
curl http://localhost:5000/api/health
curl http://localhost:8501/_stcore/health
```
Then open `http://localhost:8501`, log in as `student@uow.edu.au` /
`student123`, ask one question, confirm you get a real answer with sources
(not the fixture fallback). Paste the two curl responses and note the
outcome of the manual login/question check:

```
<paste curl output>
```

Manual login/query check: <PASS/FAIL — describe what happened>

### 2.6 — Postgres actually initialised (the cap_add check)

```powershell
docker compose logs postgres | Select-String -Pattern "database system is ready to accept connections"
```
This confirms the `CHOWN`/`SETUID`/`SETGID`/`DAC_OVERRIDE`/`FOWNER`
capabilities added back for postgres were sufficient for a genuine first-run
`initdb`, not just an existing volume. Paste output:

```
<paste here>
```

### 2.7 — ChromaDB write check (decides whether it can also go non-root later)

```powershell
docker compose exec chromadb id
docker compose logs chromadb --tail 30
```
Paste both — if chromadb logs show it accepted writes without a permission
error, note that in Section 3 as evidence for a follow-up non-root pass:

```
<paste here>
```

### 2.8 — Upload a real document (exercises the uploads_data volume as the non-root api user)

Upload any small PDF through the Streamlit UI as `lecturer@uow.edu.au` /
`lecturer123`. Confirm indexing completes (status moves to `indexed`, not
stuck on `queued`/`failed`). Paste what you observed:

```
<paste here>
```

---

## 3. Findings and follow-ups

| # | Finding | Action |
|---|---------|--------|
| 1 | <e.g. "ChromaDB started clean as non-default user, no permission errors"> | <e.g. "safe to add non-root user to chromadb in a follow-up task"> |
| 2 | | |

---

## 4. Result

**Overall Result:** <PASS / FAIL>

Confirms the done-when condition: <yes/no — every service runs with
reduced privileges (Section 0) and the stack starts cleanly from scratch
(Section 2.2)>.

---

## 5. Sign-off

- [] This file is a finalised file with a fully running test
- [x] This file committed to `feature/tung-sprint10` and pushed