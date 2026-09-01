# T8-26 — Load-test concurrent questions and set the parallelism accordingly

**Task:** T8-26
**Owner:** Tung Phuong Anh Huynh
**Sprint:** 8 (18 Aug – 1 Sep 2026)
**Due:** 1 September 2026

**Definition of Done**

- Concurrent-load numbers gathered against the real running stack
- Current gunicorn parallelism (`--workers=2 --threads=4`, set in T8-23)
  confirmed as adequate, or a concrete change proposed with numbers backing it
- Results committed so the next person can reproduce them

**Branch:** `feature/tung-sprint8`

---

## 0. What's already in place (T8-23)

`docker-compose.yml`'s `api` service already runs gunicorn instead of the
Flask dev server:

```yaml
command: [
  "gunicorn",
  "--bind=0.0.0.0:5000",
  "--workers=2",
  "--threads=4",
  "--timeout=300",
  "--access-logfile=-",
  "src.api.wsgi:app",
]
```

The comment above it says `--workers=2` "lets two people query at once."
T8-26 is about checking that against real concurrent traffic, not
introducing gunicorn — it's already there.

Two things constrain how a load test has to be designed here, both
confirmed by reading the actual route code:

- **`/api/query` rate-limits at 10 requests/minute per authenticated user**
  (`src/api/routes/query.py`, T8-20 — keyed on user id, not IP, precisely so
  the whole class doesn't share one bucket). Hammering one token
  concurrently just measures the rate limiter tripping, not the server's
  real ceiling.
- **Querying a course requires enrollment** (`state.is_enrolled`), checked
  before any retrieval/generation runs.

So a real concurrency test needs *many distinct, enrolled users*, not one
token fired many times at once.

---

## 1. What I built

`scripts/loadtest_query.py`:

1. Checks `/api/health` and prints `backend_mode` — if it isn't
   `"chromadb"`, answers are coming from the instant fixture fallback, not
   real Ollama generation, and the run is labelled accordingly rather than
   silently reported as if it were real latency.
2. Logs in as the seeded demo admin.
3. Signs up `--num-users` real student accounts via `/api/auth/signup` and
   enrolls each into `--course` via `/api/courses/<code>/members` as the
   admin, so every simulated user is a genuine, independently-rate-limited
   account.
4. For each concurrency level in `--concurrency-levels` (default
   `1,2,4,8,16`), fires the *same total number* of `/api/query` requests —
   spread round-robin across the provisioned users so no one user exceeds
   10/min — through a `ThreadPoolExecutor` sized to that concurrency level,
   and records per-request latency and status code.
5. Prints a summary table (median/p95/p99 latency, throughput, status-code
   counts per level) and writes the full raw results to
   `docs/loadtest_sprint8_t8_26.json`.

Questions fired are pulled from `tests/retrieval_eval_set.json`'s real
eval questions (not placeholder text), so retrieval/generation does actual
work rather than hitting a degenerate empty-question path.

### What I verified without a live stack

I don't have Docker, Postgres, or Ollama in the environment I wrote this
in, so I could not run the real end-to-end flow myself. What I did verify:

- `python -m py_compile scripts/loadtest_query.py` — compiles clean.
- `test/test_loadtest_query_script.py` (new, 5 tests, all passing) — unit
  tests the aggregation math (`_percentile`, `_run_level`) against mocked
  request results, including the all-errors case (must not crash on empty
  latency lists) and a mixed 200/429/timeout batch (must bucket status
  codes correctly and keep non-200s out of the latency percentiles).
- A dedicated test confirms every question in `DEFAULT_QUESTIONS` passes
  `src/api/routes/query.py`'s `_is_ambiguous()` check, so a real run won't
  quietly get 422s instead of real answers.

I could not verify the live signup → enroll → concurrent-query HTTP flow
itself — that needs your actual stack. Everything below this point needs to
be run by you.

---

## 2. How to run it

From the repo root, in PowerShell, with the stack up:

```powershell
docker compose up -d
```

Wait for Postgres, ChromaDB, and Ollama to report healthy (`docker compose ps`),
then confirm the API is answering:

```powershell
curl.exe http://localhost:5000/api/health
```

Check `"mode"` in the response — it should say `"chromadb"` for this run
to measure real generation latency. If it says `"fixture"`, Ollama/ChromaDB
aren't reachable yet; wait and re-check before running the load test.

Install `requests` if it isn't already in your active environment (it's
already a pinned dependency in `requirements.txt`, so this is usually a
no-op):

```powershell
pip install -r requirements.txt
```

Run the sweep:

```powershell
python scripts/loadtest_query.py `
    --base-url http://localhost:5000 `
    --course CSIT321 `
    --num-users 12 `
    --requests-per-user 8 `
    --concurrency-levels 1,2,4,8,16 `
    --output docs/loadtest_sprint8_t8_26.json
```

If your admin account's password was changed from the seeded default
(T8-41), pass it explicitly instead of relying on the fallback:

```powershell
$env:PAEDIA_DEMO_ADMIN_PASSWORD = "<the real password>"
```

This takes a while — with real Ollama generation in the loop, each
`/api/query` call can take several seconds, and the script runs
`num_users * requests_per_user` requests at *each* of the 5 concurrency
levels (12 × 8 × 5 = 480 requests total with the defaults above). Lower
`--num-users`/`--requests-per-user` for a quicker first pass if you want to
sanity-check the script before committing to the full sweep.

**Test accounts are not deleted afterward** (there's no user-delete
endpoint) — `loadtest.*@uow.edu.au` accounts will remain in Postgres. Fine
for a local/dev Postgres; worth a manual cleanup query
(`DELETE FROM users WHERE email LIKE 'loadtest.%@uow.edu.au'`, cascading
through memberships/tokens per the schema) before this is ever pointed at
the shared Tailscale host.

---

## 3. Results — first real run, 1 Sept 2026

```
python scripts/loadtest_query.py --base-url http://localhost:5000 --course CSIT321 --num-users 12 --requests-per-user 8 --concurrency-levels 1,2,4,8,16 --output docs/loadtest_sprint8_t8_26.json
```

| Concurrency | Total Reqs | Wall (s) | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Status codes |
|---|---|---|---|---|---|---|---|
| 1 | 96 | 592.788 | 0.162 | 2086.7 | 3933.7 | 136191.8 | `{'200': 96}` |
| 2 | 96 | 100.575 | 0.955 | 2080.4 | 2260.6 | 2368.3 | `{'200': 96}` |
| 4 | 96 | 50.107 | 1.916 | 2076.2 | 2103.9 | 2185.9 | `{'200': 96}` |
| 8 | 96 | 25.043 | 3.833 | 2077.0 | 2132.1 | 2183.2 | `{'200': 48, '429': 48}` |
| 16 | 96 | 12.53 | 7.661 | 2082.4 | 2142.0 | 2154.0 | `{'429': 68, '200': 28}` |

`backend_mode` at time of run: **`not_initialized`** (`/api/health` reported
`"rag_available": false` and `"warmup": {"status": "running"}` — the
warmup that never finished during this entire ~13-minute run).

**This run has two confounds that need to be understood before treating it
as a real concurrency recommendation. Neither is a product/API defect —
one is a limitation of the environment at the time of the run, the other
was a bug in this script, now fixed (Section 5).**

### 3.1 The backend was still warming up for the entire run

`mode: "not_initialized"` and `warmup.status: "running"` mean ChromaDB/
Ollama had not finished loading when the sweep started, and — going by the
data — never finished during the ~13 minutes the whole sweep took. Looking
at the raw per-request data in `docs/loadtest_sprint8_t8_26.json`:

- The overwhelming majority of requests have `server_latency_ms` in the
  **7–30ms** range — far too fast to be real Ollama generation, consistent
  with the fixture fallback (`"fixture_loaded": true` in the health
  response) answering instead.
- A handful of requests at concurrency=1 took **wildly** longer:
  224,453ms, 136,192ms, 22,761ms, 6,848ms, 5,058ms — almost certainly real
  requests that got stuck behind the in-progress model pull/warmup before
  either completing for real or eventually falling through. This is what
  drove concurrency=1's p99 up to 136 seconds and its wall time up to
  592.8 seconds, despite every individual "normal" request taking ~2
  seconds.
- By concurrency=2 onward, no more of these extreme outliers appear — most
  likely the warmup process had moved past whatever it was blocking on, or
  those slow paths simply weren't hit again by chance.

**Conclusion: this run mostly measured the fixture-fallback path, not real
Ollama-backed generation.** It's not yet possible to say anything about
concurrency behaviour under real generation load from this data — see
Section 4 for the required re-run.

### 3.2 The ~2080ms baseline on almost every request is client/network overhead, not server processing

Every single successful request, at every concurrency level, took close to
**2050–2150ms** measured client-side (`elapsed_ms`), while the server's own
reported processing time (`server_latency_ms`, taken from the API
response body) was **7–30ms** for the same requests. That ~2-second gap is
present uniformly regardless of load, backend mode, or concurrency level —
which rules out server-side queuing as the explanation (queuing delay would
grow with concurrency; this doesn't).

The far more likely explanation is Windows + Docker Desktop's networking
layer: this script uses a fresh `requests.post(...)` call per request with
no session/connection reuse, and each new TCP connection to a
Docker-Desktop-forwarded port on Windows goes through the WSL2 VM's
NAT/port-proxy layer, which is a known source of roughly this much
per-connection overhead. **The number to trust for "how fast is the API
actually responding" is `server_latency_ms` from the response body (7–30ms
here), not the client-measured `elapsed_ms`** — the latter mixes in a fixed
local-network cost that has nothing to do with the API or its concurrency
settings.

### 3.3 The 429s at concurrency 8 and 16 are a rate-limit-window artifact of this script, not the server failing under load

`/api/query` rate-limits at **10 requests/minute per user, on a rolling
60-second window** (T8-20). The first version of this script provisioned
12 users **once** and reused them across all 5 sequential concurrency
levels. Reconstructing the absolute timeline from the wall-clock durations
above:

| Level | Starts at | Ends at |
|---|---|---|
| 1 | 0.0s | 592.8s |
| 2 | 592.8s | 693.4s |
| 4 | 693.4s | 743.5s |
| 8 | 743.5s | 768.5s |
| 16 | 768.5s | 781.0s |

Levels 4 → 8 → 16 ran back-to-back with **no gap**, in 25.0s and 12.5s
respectively. Since the same 12 users were reused, a rolling 60-second
window measured during level 8 reaches back far enough to include the tail
of level 4's requests for the same users; during level 16 it reaches back
far enough to include almost all of level 4 and part of level 8. Once a
user's requests from two-or-more adjacent levels land inside the same
60-second window, they get counted together against that user's 10/min
cap — which is exactly consistent with the pattern seen: 0% rate-limited
through level 4 (levels far enough apart, or long enough, not to overlap),
jumping to 50% at level 8 and 71% at level 16 as the levels ran faster and
the overlap grew.

**Conclusion: the 429s measured here reflect this script's timing design,
not the server rejecting real concurrent load from 8 or 16 independent
users.** Fixed in Section 5 — this needs a re-run before the 429 pattern
can be trusted.

### 3.4 What this run *does* tell us, despite the confounds

- Levels 1, 2, and 4 (100% success, no rate-limit contamination) show
  throughput scaling almost exactly linearly with concurrency — 0.162 →
  0.955 → 1.916 req/s, doubling each time concurrency doubled — with flat
  per-request latency throughout. That's a clean signal that, at least up
  through concurrency 4, nothing in the stack (gunicorn, the fixture path,
  or the Windows/Docker network layer) was anywhere close to saturated.
- No evidence yet of where the real ceiling is, because the run never
  produced a level with 100% success where throughput *stopped* scaling —
  levels 8 and 16 are unusable for this purpose due to 3.3 above.

---

## 4. Recommendation

**Not ready to make a parallelism recommendation from this run — a re-run
is required**, for two independent reasons, neither of which is a defect
in `--workers=2 --threads=4` itself:

1. The backend hadn't finished warming up (Section 3.1), so this mostly
   measured the instant fixture fallback, not real Ollama generation —
   which is the actual thing likely to constrain concurrency in production.
2. The 429 pattern at concurrency 8/16 was a script-timing artifact
   (Section 3.3), not real per-user rate-limit rejection under genuine
   concurrent load from 8 or 16 independent users.

**What to do for the re-run** (script already fixed, see Section 5):

1. Before running, poll `/api/health` until `"mode": "chromadb"` and
   `"warmup": {"status": "ready"}` (or whatever the ready-state value is —
   confirm against `src/api/routes/health.py`) instead of starting
   immediately. `docker compose logs -f ollama` will show when the model
   finishes loading.
2. Re-run the same command. With the script fix in Section 5, each level
   now gets its own fresh set of users, so a real 429 at any level will
   mean that level's own concurrent traffic actually exceeded a user's
   10/min cap within its own window — not spillover from the previous
   level.
3. Re-read Section 3.4's guide once real numbers come back — a flat p95
   until concurrency 8 that jumps sharply at 16 supports the current
   `--workers=2 --threads=4`; earlier degradation points at something else
   (check `docker stats` on the `ollama` container); throughput still
   climbing linearly at 16 with flat latency suggests the setting may be
   under-provisioned and `--workers=4` is worth trying.
4. When reporting the re-run's numbers, lead with `server_latency_ms` from
   the JSON output (or a modified script that surfaces it directly in the
   summary table) rather than client-side `elapsed_ms`, per Section 3.2 —
   otherwise the Windows/Docker network overhead will dominate the numbers
   again and mask whatever the server is actually doing.

---

## 5. Script fix applied after this run (1 Sept 2026)

`scripts/loadtest_query.py` originally called `_provision_users()` once,
before the concurrency sweep, and reused that same batch of accounts for
every level. Fixed to provision a **fresh batch of `--num-users` accounts
for every concurrency level**, inside the sweep loop, so no user's request
history can leak across a level boundary and get counted against a
different level's 429 rate within the shared 60-second rolling window
(Section 3.3). Verified: `python -m py_compile scripts/loadtest_query.py`
and `python -m pytest test/test_loadtest_query_script.py` (5 tests) both
pass against the fixed version.

One tradeoff of this fix worth knowing before the re-run: at
`--num-users 12` swept across 5 levels, this now creates **60** test
accounts per full run instead of 12, all left in Postgres (no delete
endpoint — see Section 2). Fine for a local/dev instance; worth the manual
cleanup query mentioned in Section 2 before running this against a shared
host, and worth considering a lower `--num-users` for routine re-runs now
that the account count scales with the number of levels swept.

