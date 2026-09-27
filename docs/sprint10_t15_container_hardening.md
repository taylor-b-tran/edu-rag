# T15 — Container hardening

**Task:** T15 (Sprint 10)
**Owner:** Tung Phuong Anh Huynh
**Checked by:** Tai
**Sprint:** 10
**Status (27 Sept, Taylor's review of PR #134): DEFERRED, not in this PR.**

Taylor's review found the hardening in `docker-compose.yml` (`cap_drop`,
`security_opt`, `cap_add` on every service) had never been tried on the GPU
host, and a single `docker compose up -d` recreates all five containers with
it four days before the 1 Oct recording — too close to the deadline to risk
untested. The Dockerfile's non-root `edurag` user has a second, separate
problem: the live host's `uploads_data` volume is already owned by root from
every previous (root) container run, so the first rebuild under the new user
would 500 on every upload and leave orphaned files behind on every delete.

**Both changes have been reverted in this PR** — `docker-compose.yml` no
longer sets `cap_drop`/`security_opt`/`cap_add` on any service, and
`docker/Dockerfile.demo` no longer creates or switches to the `edurag` user.
Everything below is kept as the plan for redoing this properly after the
1 Oct recording — a template for next time, not a report of something
already verified. Do not run Section 2's commands against the live host in
the meantime.

---

## 0. What's actually planned (next sprint, not this one)

| Service | Planned change | Extra step this needs first |
|---------|-----------------|------------------------------|
| `api` / `streamlit` | non-root `edurag` user (uid 10001), `cap_drop: [ALL]`, `security_opt: no-new-privileges:true` | `chown -R 10001:10001` the **existing** `uploads_data` volume on the live host first, and give the user a real `HOME` (nothing does today) — both untested, per Taylor's review |
| `app` (tools container, `profiles: tools`) | stays root deliberately — interactive debug shell, never auto-started, never exposed on a port | none |
| `postgres` | `cap_drop: [ALL]` + `cap_add: [CHOWN, SETUID, SETGID, DAC_OVERRIDE, FOWNER]` for the official entrypoint's first-run `initdb` | verify against a copy of the **live** `postgres_data`, not only an empty volume |
| `chromadb` | `cap_drop: [ALL]`, no-new-privileges | verify the image's default user can still write `/data` under this |
| `ollama` | `cap_drop: [ALL]`, no-new-privileges only — stays root, read-write | GPU passthrough must be confirmed working on the actual GPU host before any user change here; this is the one most likely to silently break the recording if rushed |

---

## 1. Why this needs its own temporary stack, not the live one

`docker-compose.yml` declares `name: edurag` at the top. That is the
project name Docker Compose uses to identify a stack's containers, networks
and volumes — and it is the exact name the live deployment on the GPU host
already runs under. Any `docker compose down -v` run from a checkout of this
file, on that host, drops the live `postgres_data`, `chromadb_data`,
`ollama_data`, and `uploads_data` volumes — all of it, not a copy.

**Every command below must run against a separate project name**, so it
creates and destroys its own throwaway containers/volumes and cannot touch
the live ones even by mistake:

```powershell
# From a checkout of this branch, NOT the live host's own directory:
$env:COMPOSE_PROJECT_NAME = "edurag-t15-verify"
```

Everything in Section 2 assumes `COMPOSE_PROJECT_NAME` is set this way for
the whole session. If a new shell is opened partway through, set it again
before running anything else. **Never run any command in this file from the
live host's own deployment directory — clone or copy this branch out to a
separate path first**, so there is no way to be in the right directory with
the wrong project name, or the right project name with the wrong `-p` flag
forgotten on one command.

---

## 2. Verification steps (for the follow-up task, not this PR)

Run these in order, from the separate checkout described in Section 1, with
`COMPOSE_PROJECT_NAME` set.

### 2.1 — Config validates

```powershell
docker compose config --quiet
```

### 2.2 — Full stack builds and starts clean from a cold volume set

This recreates `postgres_data`/`chromadb_data`/etc. from empty — safe here
because `COMPOSE_PROJECT_NAME` scopes them to `edurag-t15-verify`, not the
live stack's volumes.

```powershell
docker compose down -v
docker compose up -d --build
docker compose ps
```

### 2.3 — Confirm the api/streamlit containers are actually non-root

```powershell
docker compose exec api id
docker compose exec streamlit id
```
Expected: `uid=10001(edurag) gid=10001(edurag)` for both.

### 2.4 — Confirm capabilities were actually dropped

```powershell
docker compose exec api sh -c "cat /proc/1/status | grep Cap"
```

### 2.5 — App still works end to end

```powershell
curl http://localhost:5000/api/health
curl http://localhost:8501/_stcore/health
```
Then log in as `student@uow.edu.au`, ask one question, confirm a real
answer with sources.

### 2.6 — Postgres actually initialised (the cap_add check)

```powershell
docker compose logs postgres | Select-String -Pattern "database system is ready to accept connections"
```

### 2.7 — Upload volume ownership, against a copy of the live data

Before trying the non-root user against the real `uploads_data`, copy it
into this temporary project rather than pointing at the live volume
directly:

```powershell
docker run --rm -v edurag_uploads_data:/from -v edurag-t15-verify_uploads_data:/to alpine \
  sh -c "cp -a /from/. /to/"
docker compose exec api sh -c "chown -R 10001:10001 /workspace/data/uploads && ls -la /workspace/data/uploads"
```
Confirm ownership changed with no errors, then repeat 2.5's upload/query
check against this copy.

### 2.8 — ChromaDB write check

```powershell
docker compose exec chromadb id
docker compose logs chromadb --tail 30
```

### 2.9 — GPU passthrough with ollama (the step most likely to break silently)

Run only once a GPU-equipped machine is available for this check —a laptop
without one cannot confirm this either way:

```powershell
docker compose exec ollama ollama list
docker compose exec ollama nvidia-smi
```
If `nvidia-smi` fails inside the container after the hardening is applied
here but succeeded before, stop — that is the change to roll back, not push
past.

---

## 3. Result

Not yet run. This section stays a template until the follow-up task
actually executes Section 2 against the temporary stack described in
Section 1.

**Overall Result:** DEFERRED — see the status note at the top of this file.

---

## 4. Sign-off

- [ ] This file is a finalised file with a fully running test
- [x] Hardening reverted from this PR (`docker-compose.yml`,
      `docker/Dockerfile.demo`) per Taylor's 27 Sept review
- [ ] Follow-up task scheduled for after the 1 Oct recording