"""One-command health check for the Paedia demo stack (Sprint 6, T29).

Run this after `docker compose up -d --build` (or the `-f docker-compose.gpu.yml`
overlay) to get a single PASS/FAIL/WARN readout per service, instead of manually
checking `docker compose ps` plus four different curl commands.

Usage (from the repo root, after the stack is up):

    python scripts/check_demo_ready.py

Exit code is 0 if everything is ready to demo, 1 otherwise (so this can also be
used as a CI/script gate, not just an interactive check).

Only uses the Python standard library — no extra pip install required beyond
what's already needed to have Docker running.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Same defaults as .env.example — override via environment variables if your
# ports differ.
API_PORT = os.environ.get("API_PORT", "5000")
APP_PORT = os.environ.get("APP_PORT", "8501")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _http_get_json(url: str, timeout: float = 10.0) -> tuple[int, dict | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, None, str(exc)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, None, str(exc)
    try:
        return status, json.loads(body), body
    except json.JSONDecodeError:
        return status, None, body


def _compose_ps() -> list[dict]:
    """Return `docker compose ps --format json` rows, one dict per service."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[FAIL] Could not run `docker compose ps` — is Docker running? ({exc})")
        return []
    rows = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def check_container_status(rows: list[dict]) -> dict[str, tuple[str, str]]:
    """docker-level State/Health per service. Postgres/API/Streamlit have a
    Docker healthcheck; ChromaDB/Ollama don't, so 'running' is the best we get
    from this layer alone (the HTTP checks below cover them properly)."""
    by_service = {row.get("Service"): row for row in rows}
    results: dict[str, tuple[str, str]] = {}
    for service in ("postgres", "chromadb", "ollama", "api", "streamlit"):
        row = by_service.get(service)
        if row is None:
            results[service] = (FAIL, "container not found/not running - did `docker compose up` run?")
            continue
        state = row.get("State", "")
        health = row.get("Health", "")
        if state != "running":
            results[service] = (FAIL, f"state={state or 'unknown'}")
        elif health == "healthy" or health == "":
            results[service] = (PASS, f"state=running health={health or 'n/a'}")
        else:
            results[service] = (FAIL, f"state=running health={health}")
    return results


def check_api() -> tuple[str, str]:
    status, body, raw = _http_get_json(f"http://localhost:{API_PORT}/api/health")
    if body is None:
        return FAIL, f"GET /api/health failed ({raw})"
    if body.get("status") != "ok":
        return FAIL, f"unexpected response: {raw[:200]}"
    warmup = body.get("warmup", {})
    if warmup.get("status") == "ok":
        return PASS, f"model={warmup.get('model')} warmup_ms={warmup.get('elapsed_ms')}"
    if warmup.get("status") == "running":
        return WARN, "warm-up still in progress — wait a few seconds and re-run"
    return WARN, f"warm-up status={warmup.get('status')}: {warmup.get('error')}"


def check_streamlit() -> tuple[str, str]:
    status, _, raw = _http_get_json(f"http://localhost:{APP_PORT}/_stcore/health")
    if status == 200 and raw.strip().lower() == "ok":
        return PASS, "http 200 ok"
    return FAIL, f"GET /_stcore/health -> status={status}, body={raw[:100]!r}"


def check_chromadb() -> tuple[str, str]:
    status, body, raw = _http_get_json(f"http://localhost:{CHROMA_PORT}/api/v2/heartbeat")
    if body and "nanosecond heartbeat" in body:
        return PASS, "heartbeat ok"
    return FAIL, f"GET /api/v2/heartbeat failed (status={status}, body={raw[:150]!r})"


def check_ollama() -> tuple[str, str]:
    status, body, raw = _http_get_json(f"http://localhost:{OLLAMA_PORT}/api/tags")
    if body is None:
        return FAIL, f"GET /api/tags failed ({raw})"
    models = body.get("models", [])
    if not models:
        return WARN, "no models pulled yet — first warm-up may still be pulling"
    names = ", ".join(m.get("name", "?") for m in models)
    return PASS, f"models available: {names}"


def main() -> int:
    print("Paedia demo readiness check\n" + "=" * 32)

    rows = _compose_ps()
    container_results = check_container_status(rows)

    checks = [
        ("postgres (container)", container_results.get("postgres", (FAIL, "n/a"))),
        ("chromadb (container)", container_results.get("chromadb", (FAIL, "n/a"))),
        ("chromadb (heartbeat)", check_chromadb()),
        ("ollama (container)", container_results.get("ollama", (FAIL, "n/a"))),
        ("ollama (models)", check_ollama()),
        ("api (container)", container_results.get("api", (FAIL, "n/a"))),
        ("api (/api/health)", check_api()),
        ("streamlit (container)", container_results.get("streamlit", (FAIL, "n/a"))),
        ("streamlit (/_stcore/health)", check_streamlit()),
    ]

    worst = PASS
    for name, (result, detail) in checks:
        print(f"[{result:>4}] {name:<28} {detail}")
        if result == FAIL:
            worst = FAIL
        elif result == WARN and worst != FAIL:
            worst = WARN

    print("=" * 32)
    if worst == PASS:
        print("READY - all services healthy. Open http://localhost:%s to demo." % APP_PORT)
        return 0
    if worst == WARN:
        print("NOT READY YET - one or more services still warming up. Wait ~15s and re-run.")
        return 0
    print("FAIL - see the [FAIL] lines above. Check `docker compose logs <service>`.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
