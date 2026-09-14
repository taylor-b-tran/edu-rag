# Sprint 9 -- Retrieval Tuning Check (T9-10)

**Corpus size at run time: 3147 chunks.**

Ranking-quality re-run of the Sprint 7 benchmark: see `docs/retrieval_benchmark_sprint9.md` (produced by `BENCHMARK_SPRINT=9 python scripts/benchmark_retrieval.py`) for the full per-query table. This report covers the other half of T9-10: whether `SIMILARITY_THRESHOLD` still holds up on the wider corpus.

## Before / After -- ranking quality

| Metric | Sprint 7 (46 chunks) | Sprint 9 (this corpus) |
|---|---:|---:|
| Precision@5 | 0.2 | 0.2 |
| Recall@10 | 1.0 | 1.0 |
| MRR | 0.925 | 0.925 |

## Threshold sweep

Current production default: `SIMILARITY_THRESHOLD = 0.35`.

| Threshold | In-corpus false fallbacks | Off-topic correct fallbacks | Off-topic false accepts |
|---:|---:|---:|---:|
| 0.2 | 0 (--) | 0/2 | 2 (R21, R22) |
| 0.25 | 0 (--) | 1/2 | 1 (R21) |
| 0.3 | 0 (--) | 1/2 | 1 (R21) |
| 0.35 (current) | 1 (R01) | 2/2 | 0 (--) |
| 0.4 | 1 (R01) | 2/2 | 0 (--) |
| 0.45 | 1 (R01) | 2/2 | 0 (--) |
| 0.5 | 4 (R01, R02, R03, R06) | 2/2 | 0 (--) |

## Recommendation

**Recommended threshold: 0.35** (no change from current default 0.35).

No threshold in the grid separates in-corpus from off-topic questions cleanly on this corpus. Keeping the current default (0.35) and flagging for manual review rather than picking a value that still gets some queries wrong.
