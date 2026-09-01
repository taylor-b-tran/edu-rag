"""
T8-26 — Load-test concurrent questions and set the parallelism accordingly.

Owner: Tung Phuong Anh Huynh
Sprint: 8 (18 Aug - 1 Sep 2026)

Fires concurrent, authenticated /api/query requests against a *running*
EduRAG stack (real docker-compose stack, not the pytest test_client) across
a matrix of concurrency levels, and reports latency/error-rate per level.
The goal is to find where gunicorn's current `--workers=2 --threads=4`
(docker-compose.yml, T8-23) starts to fall over, so the setting can be
confirmed or tuned with real numbers instead of a guess.

Why this signs up real users instead of hammering one token:
    /api/query rate-limits at 10 requests/minute PER AUTHENTICATED USER
    (src/api/routes/query.py, T8-20), and requires the caller to be
    enrolled in the course being queried (state.is_enrolled). Reusing one
    demo token across many concurrent threads would just measure the rate
    limiter tripping (429s), not the server's real concurrency ceiling. This
    script creates N distinct student accounts via /api/auth/signup, enrolls
    each into the target course via an admin account, and spreads requests
    across them round-robin so no single user's 10/min cap is the
    bottleneck being measured.

Requires:
    - The stack running and reachable at --base-url (default
      http://localhost:5000), i.e. `docker compose up -d`.
    - Postgres reachable (signup and course enrollment both need it -
      db_available must be true, or signup returns 503).
    - An admin account. Defaults to the seeded demo admin
      (admin@uow.edu.au); password comes from PAEDIA_DEMO_ADMIN_PASSWORD if
      set on the api container, else the seeded fallback "admin123".

Usage (see docs/loadtest_sprint8_t8_26.md for full walkthrough):

    python scripts/loadtest_query.py `
        --base-url http://localhost:5000 `
        --course CSIT321 `
        --num-users 12 `
        --requests-per-user 8 `
        --concurrency-levels 1,2,4,8,16 `
        --output docs/loadtest_sprint8_t8_26.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]

# Real questions from the eval set (tests/retrieval_eval_set.json) rather
# than lorem-ipsum text, so retrieval/generation does real work instead of
# hitting a trivially-cached or trivially-empty path. Cycled round-robin
# across requests. All are >3 words and don't match _AMBIGUOUS_PATTERNS in
# src/api/routes/query.py, so none of these get rejected with 422.
DEFAULT_QUESTIONS = [
    "What does RAG stand for and how does it reduce hallucination?",
    "What are the three core components of a RAG pipeline?",
    "What embedding model does EduRAG use and how many dimensions does it produce?",
    "What chunk size and overlap does EduRAG use by default and why?",
    "What metadata fields does ChromaDB store for each chunk in EduRAG?",
    "How do you filter a ChromaDB query so it only returns results from one course?",
    "Explain how Flask routes an incoming API request to a handler function.",
    "What does Ollama do differently from calling the OpenAI API directly?",
    "Why does the system fall back to a much worse retrieval method when the internet drops?",
    "What is the purpose of the confidence score returned with a generated answer?",
]


def _random_suffix() -> str:
    return uuid.uuid4().hex[:10]


def _login(base_url: str, email: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Admin login failed ({resp.status_code}): {resp.text}\n"
            "Check --admin-email/--admin-password, or set "
            "PAEDIA_DEMO_ADMIN_PASSWORD to match the running stack."
        )
    return resp.json()["access_token"]


def _signup_student(base_url: str) -> dict[str, Any]:
    suffix = _random_suffix()
    email = f"loadtest.{suffix}@uow.edu.au"
    resp = requests.post(
        f"{base_url}/api/auth/signup",
        json={
            "email": email,
            "username": f"loadtest_{suffix}",
            "password": f"LoadTest!{suffix}",
            "role": "student",
        },
        timeout=30,
    )
    if resp.status_code != 201:
        raise RuntimeError(f"Signup failed for {email} ({resp.status_code}): {resp.text}")
    body = resp.json()
    return {"email": email, "access_token": body["access_token"]}


def _enroll(base_url: str, admin_token: str, course_code: str, email: str) -> None:
    resp = requests.post(
        f"{base_url}/api/courses/{course_code}/members",
        json={"email": email, "membership_role": "student"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Enrolling {email} into {course_code} failed "
            f"({resp.status_code}): {resp.text}"
        )


def _provision_users(base_url: str, admin_token: str, course_code: str, num_users: int) -> list[dict[str, Any]]:
    users = []
    for i in range(num_users):
        user = _signup_student(base_url)
        _enroll(base_url, admin_token, course_code, user["email"])
        users.append(user)
        print(f"  provisioned user {i + 1}/{num_users}: {user['email']}")
    return users


def _fire_one(base_url: str, token: str, course_code: str, question: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        resp = requests.post(
            f"{base_url}/api/query",
            json={"query": question, "course_id": course_code},
            headers={"Authorization": f"Bearer {token}"},
            timeout=310,  # gunicorn --timeout=300 in docker-compose.yml
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status_code": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "server_latency_ms": resp.json().get("latency_ms") if resp.status_code == 200 else None,
            "error": None,
        }
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {"status_code": None, "elapsed_ms": elapsed_ms, "server_latency_ms": None, "error": str(exc)}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[idx]


def _run_level(
    base_url: str,
    users: list[dict[str, Any]],
    course_code: str,
    concurrency: int,
    requests_per_user: int,
    questions: list[str],
) -> dict[str, Any]:
    tasks = []
    for req_idx in range(requests_per_user):
        for user in users:
            question = questions[(req_idx + hash(user["email"])) % len(questions)]
            tasks.append((user["access_token"], question))

    results: list[dict[str, Any]] = []
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(_fire_one, base_url, token, course_code, question)
            for token, question in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())
    wall_seconds = time.perf_counter() - wall_start

    latencies = [r["elapsed_ms"] for r in results if r["status_code"] == 200]
    status_counts: dict[str, int] = {}
    for r in results:
        key = str(r["status_code"]) if r["status_code"] is not None else "connection_error"
        status_counts[key] = status_counts.get(key, 0) + 1

    return {
        "concurrency": concurrency,
        "total_requests": len(tasks),
        "wall_seconds": round(wall_seconds, 3),
        "throughput_rps": round(len(tasks) / wall_seconds, 3) if wall_seconds > 0 else 0.0,
        "status_counts": status_counts,
        "success_count": len(latencies),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 1) if latencies else None,
            "median": round(statistics.median(latencies), 1) if latencies else None,
            "p95": round(_percentile(latencies, 95), 1) if latencies else None,
            "p99": round(_percentile(latencies, 99), 1) if latencies else None,
            "max": round(max(latencies), 1) if latencies else None,
        },
        "raw_results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--course", default="CSIT321")
    parser.add_argument("--num-users", type=int, default=10)
    parser.add_argument("--requests-per-user", type=int, default=8,
                         help="Kept <= 10 by default so no single user's 10/min rate limit "
                              "(src/api/routes/query.py) confounds the concurrency measurement.")
    parser.add_argument("--concurrency-levels", default="1,2,4,8,16",
                         help="Comma-separated list of concurrency levels to sweep.")
    parser.add_argument("--admin-email", default="admin@uow.edu.au")
    parser.add_argument("--admin-password", default=os.environ.get("PAEDIA_DEMO_ADMIN_PASSWORD") or "admin123")
    parser.add_argument("--output", default=str(REPO_ROOT / "docs" / "loadtest_sprint8_t8_26.json"))
    args = parser.parse_args()

    if args.requests_per_user > 10:
        print(
            f"WARNING: --requests-per-user={args.requests_per_user} exceeds the 10/min "
            "per-user rate limit. Expect 429s that reflect the rate limiter, not raw "
            "server concurrency. Lower this or raise --num-users instead.",
            file=sys.stderr,
        )

    concurrency_levels = [int(c.strip()) for c in args.concurrency_levels.split(",")]

    print(f"Checking {args.base_url}/api/health ...")
    health = requests.get(f"{args.base_url}/api/health", timeout=10).json()
    print(f"  backend_mode={health.get('mode')} rag_available={health.get('rag_available')} "
          f"warmup={health.get('warmup', {}).get('status')}")
    if health.get("mode") != "chromadb":
        print(
            "  WARNING: backend_mode is not 'chromadb' - answers will come from the fixture "
            "fallback, which is near-instant and will NOT reflect real Ollama generation "
            "latency. Numbers from this run should be labelled accordingly.",
            file=sys.stderr,
        )

    print(f"Logging in as admin ({args.admin_email}) ...")
    admin_token = _login(args.base_url, args.admin_email, args.admin_password)

    summary = {
        "base_url": args.base_url,
        "course": args.course,
        "num_users": args.num_users,
        "requests_per_user": args.requests_per_user,
        "backend_mode": health.get("mode"),
        "levels": [],
    }

    print(f"\n{'Concurrency':>11} | {'Reqs':>5} | {'Wall(s)':>8} | {'RPS':>7} | "
          f"{'p50(ms)':>8} | {'p95(ms)':>8} | {'p99(ms)':>8} | Status counts")
    print("-" * 100)
    for level in concurrency_levels:
        # Fresh users per level, not reused across levels. Levels run back-to-back
        # (often within seconds of each other once concurrency is high), and the
        # /api/query rate limit is a 60-second ROLLING window per user - reusing
        # the same accounts across levels lets one level's tail requests fall
        # inside the next level's window and get counted against it, producing
        # 429s that reflect this script's timing, not the server's real ceiling.
        print(f"Provisioning {args.num_users} fresh test accounts for concurrency={level} ...")
        users = _provision_users(args.base_url, admin_token, args.course, args.num_users)
        result = _run_level(args.base_url, users, args.course, level, args.requests_per_user, DEFAULT_QUESTIONS)
        summary["levels"].append(result)
        lat = result["latency_ms"]
        print(
            f"{level:>11} | {result['total_requests']:>5} | {result['wall_seconds']:>8} | "
            f"{result['throughput_rps']:>7} | {str(lat['median']):>8} | {str(lat['p95']):>8} | "
            f"{str(lat['p99']):>8} | {result['status_counts']}"
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nFull results written to {output_path}")
    print(
        "\nNote: test accounts (loadtest.*@uow.edu.au) are left in Postgres - there is no "
        "user-delete endpoint. Safe to leave for a local/dev instance; worth a manual "
        "cleanup query before this is ever pointed at a shared host."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
