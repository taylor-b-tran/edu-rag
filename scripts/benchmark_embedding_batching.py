"""T10: before/after timing benchmark for the T09 batch-encoding change.

Compares the old per-chunk model.encode() loop against the new single
batched model.encode() call, using the real seed corpus plus a larger
synthetic chunk set (to approximate a multi-page lecturer upload).

Run inside the api container, where sentence-transformers is installed:

    docker compose exec api python scripts/benchmark_embedding_batching.py
"""
from __future__ import annotations

import statistics
import time

from sentence_transformers import SentenceTransformer

from src.document_processor.seed_documents import SEED_DOCUMENTS

REPEATS = 5


def time_per_chunk_loop(model, texts: list[str]) -> float:
    t0 = time.perf_counter()
    for text in texts:
        model.encode(text, normalize_embeddings=True)
    return time.perf_counter() - t0


def time_batch(model, texts: list[str]) -> float:
    t0 = time.perf_counter()
    model.encode(texts, normalize_embeddings=True)
    return time.perf_counter() - t0


def run(label: str, texts: list[str], model) -> None:
    loop_times = [time_per_chunk_loop(model, texts) for _ in range(REPEATS)]
    batch_times = [time_batch(model, texts) for _ in range(REPEATS)]

    loop_med = statistics.median(loop_times)
    batch_med = statistics.median(batch_times)
    speedup = loop_med / batch_med if batch_med else float("inf")

    print(f"\n=== {label} ({len(texts)} chunks, {REPEATS} repeats) ===")
    print(f"  per-chunk loop : median {loop_med:.3f}s  (all: {[round(t, 3) for t in loop_times]})")
    print(f"  batched call   : median {batch_med:.3f}s  (all: {[round(t, 3) for t in batch_times]})")
    print(f"  speedup        : {speedup:.2f}x")


def main() -> None:
    print("Loading all-MiniLM-L6-v2 ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    model.encode("warm up", normalize_embeddings=True)  # exclude first-call JIT/model-load cost

    seed_texts = [doc["text"] for doc in SEED_DOCUMENTS]
    run("Seed corpus (real, T09 seed-ingest path)", seed_texts, model)

    # Approximate a larger multi-page lecturer upload (T09 upload-indexing path).
    upload_texts = (seed_texts * 4)[:60]
    run("Simulated 60-chunk upload (T09 live-upload path)", upload_texts, model)


if __name__ == "__main__":
    main()
