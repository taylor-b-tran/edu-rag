# T10 — Embedding Speed Benchmark (Before/After T09)

Real before/after timing for the T09 batch-encoding change, run inside the
`api` container (`docker compose exec api python scripts/benchmark_embedding_batching.py`)
against the actual `all-MiniLM-L6-v2` model — same model the app uses in
production, not a mock.

Methodology: 5 repeats each of the old per-chunk `model.encode()` loop vs. the
new single batched call, median reported to reduce noise. First call to the
model is a throwaway warm-up (excluded) so both sides only measure steady-state
encode time.

## Results

| Corpus | Per-chunk loop (median) | Batched call (median) | Speedup |
|---|---|---|---|
| Seed corpus, 18 chunks (real, seed-ingest path) | 9.685s | 1.123s | **8.63x** |
| Simulated 60-chunk upload (live-upload path) | 32.482s | 2.095s | **15.51x** |

Full run output (all 5 repeats per case) is in the script's stdout; see
`scripts/benchmark_embedding_batching.py` docstring for how to reproduce.

## Takeaway

Batching amortises SentenceTransformer's per-call tokenisation/forward-pass
overhead across all chunks in one shot. The speedup grows with chunk count —
8.6x at 18 chunks, 15.5x at 60 — so the live-upload path (`documents.py`,
typically many chunks per multi-page lecture upload) benefits more than the
one-off seed ingest. This confirms the T09 fix is not just correct but
measurably faster, which matters directly for demo responsiveness when a
lecturer uploads material live.
