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

## 3. Results

| Concurrency | Total Reqs | Wall (s) | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Status codes |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 4 | | | | | | | |
| 8 | | | | | | | |
| 16 | | | | | | | |

`backend_mode` at time of run: _______

---

## 4. Recommendation

Whichever way the numbers land, note the actual host spec used for the run
(CPU cores, GPU, RAM) — the right worker/thread count is a function of the
machine `docker compose up -d` is running on, not a universal constant, and
future re-runs of this script on the shared Tailscale host should be
compared against this baseline rather than assumed to match it.
