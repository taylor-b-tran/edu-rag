from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)
RETRIEVAL_WARMUP_WAIT_SECONDS = 3.0


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://ollama:11434").rstrip("/")


def _ollama_model() -> str:
    return (
        os.environ.get("DEFAULT_OLLAMA_MODEL")
        or os.environ.get("OLLAMA_MODEL")
        or "qwen3:14b"
    )

# Check whether Ollama thinking mode is enabled.
def _ollama_think() -> bool:
    return os.environ.get("OLLAMA_THINK", "false").strip().lower() in {"1", "true", "yes"}

# Get how long Ollama should keep the model loaded.
def _ollama_keep_alive() -> str:
    return os.environ.get("OLLAMA_KEEP_ALIVE", "30m")


def warmup_ollama(
    host: str | None = None,
    model: str | None = None,
    pull_timeout: int = 600,
    generate_timeout: int = 180,
) -> dict[str, Any]:
    """Pull the model (if missing) and run a tiny generate to load it into VRAM.

    Safe to call repeatedly. Network/HTTP errors are reported, not raised.
    """
    host = (host or _ollama_host()).rstrip("/")
    model = model or _ollama_model()
    started = time.time()
    result: dict[str, Any] = {
        "host": host,
        "model": model,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "pulled": False,
        "generated": False,
        "error": None,
    }

    try:
        tags = requests.get(f"{host}/api/tags", timeout=5)
        tags.raise_for_status()
        installed = {m.get("name") for m in tags.json().get("models", [])}
        already_present = model in installed
    except Exception as exc:
        result["error"] = f"tags_unreachable: {type(exc).__name__}: {exc}"
        result["elapsed_ms"] = int((time.time() - started) * 1000)
        logger.warning("Ollama warm-up could not list tags: %s", exc)
        return result

    if not already_present:
        try:
            pull = requests.post(
                f"{host}/api/pull",
                json={"name": model, "stream": False},
                timeout=pull_timeout,
            )
            pull.raise_for_status()
            result["pulled"] = True
            logger.info("Ollama pulled model %s (warm-up).", model)
        except Exception as exc:
            result["error"] = f"pull_failed: {type(exc).__name__}: {exc}"
            result["elapsed_ms"] = int((time.time() - started) * 1000)
            logger.warning("Ollama warm-up pull failed for %s: %s", model, exc)
            return result
    else:
        logger.info("Ollama model %s already present; skipping pull.", model)

    try:
        gen = requests.post(
            f"{host}/api/generate",
            json={
                "model": model,
                "prompt": "ping",
                "stream": False,
                "think": _ollama_think(),
                "keep_alive": _ollama_keep_alive(),
                "options": {"num_predict": 4, "temperature": 0.0},
            },
            timeout=generate_timeout,
        )
        gen.raise_for_status()
        result["generated"] = True
    except Exception as exc:
        result["error"] = f"generate_failed: {type(exc).__name__}: {exc}"
        logger.warning("Ollama warm-up generate failed: %s", exc)

    result["elapsed_ms"] = int((time.time() - started) * 1000)
    return result


def warmup_retrieval(state) -> None:
    """Encode before serving; bound the wait for vector-service initialization."""
    from src.document_processor.ingest_corpus import _load_embedder, get_chroma_client

    try:
        embedder, _, _ = _load_embedder()
        embedder.encode(["Course material warm-up"])
    except Exception:
        logger.exception("Embedder warm-up did not complete.")
        return

    def _build() -> None:
        try:
            get_chroma_client().heartbeat()
            state.get_generator()
        except Exception:
            logger.exception("Retrieval warm-up did not initialize the pipeline.")

    # The Chroma client has unbounded calls during construction as well as
    # heartbeat and collection access. Keep all of them off the boot thread.
    # A late successful build shares get_generator's lock with query requests.
    thread = threading.Thread(target=_build, name="retrieval-warmup", daemon=True)
    thread.start()
    thread.join(RETRIEVAL_WARMUP_WAIT_SECONDS)
    if thread.is_alive():
        logger.warning("Retrieval warm-up is still running; serving requests while it completes.")


def warmup_async(state) -> threading.Thread | None:
    """Run warmup_ollama in a background thread and stash the result on state."""
    if os.environ.get("EDURAG_OLLAMA_WARMUP", "true").lower() in {"0", "false", "no"}:
        logger.info("EDURAG_OLLAMA_WARMUP disabled; skipping background warm-up.")
        state.warmup_status = {"skipped": True}
        return None

    def _run() -> None:
        try:
            state.warmup_status = {"status": "running",
                                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            outcome = warmup_ollama()
            outcome["status"] = "ok" if outcome.get("generated") else "degraded"
            state.warmup_status = outcome
            logger.info("Ollama warm-up finished: %s", outcome)
        except Exception as exc:
            state.warmup_status = {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            }
            logger.exception("Ollama warm-up crashed: %s", exc)

    thread = threading.Thread(target=_run, name="ollama-warmup", daemon=True)
    thread.start()
    return thread
