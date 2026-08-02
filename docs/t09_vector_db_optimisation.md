# T09 — Vector DB / Embedding Optimisation

**Task:** T09
**Owner:** Thanh Binh Tran
**Sprint:** 6 (27 Jul – 7 Aug 2026)
**Due:** 3 Aug 2026

## What changed

Both places that generate embeddings for storage were calling `model.encode()` once per chunk, inside a loop:

- `src/document_processor/ingest_corpus.py` — seed corpus ingestion (18 docs)
- `src/api/routes/documents.py::_bg_index_document` — the **live** lecturer-upload indexing path, which runs on every real document upload during the demo

Both now batch-encode all chunk texts in a single `model.encode(list_of_texts, normalize_embeddings=True)` call instead of one call per chunk. SentenceTransformer amortises tokenisation and forward-pass overhead across a batch, so this is faster per document without changing the embeddings produced (same model, same inputs, same normalisation — output vectors are identical, only the call pattern changed). Compatible with both the real `SentenceTransformer` and the CI-only `OfflineEmbedder` fallback, since both accept a list input to `.encode()`.

The upload path (`documents.py`) is the more impactful of the two — it runs on every live upload during the actual demo, not just once at seed time.

## Verification

| Check | Result |
|---|---|
| `docker compose exec -T api python -m pytest test -q` (excluding live-generation tests) | PASS — 117 passed, 1 deselected, 0 failed |
| Real upload as lecturer (`t09_test_upload.docx`, 5 paragraphs → multiple chunks) via `/api/upload` | PASS — indexing job reached `completed`, 100% |
| Query as student for content unique to the test upload | PASS — correct answer, cited `t09_test_upload.docx` |
| Cleanup — `DELETE /api/document/{id}` | PASS — test document removed, corpus back to seed state |

## Not done here (separate task)

A rigorous timing benchmark (batch vs. per-item, repeated runs, statistical comparison) is T10's job. This change is verified *correct*, not yet formally *benchmarked* — batch encoding is a well-documented SentenceTransformers speedup, but an honest before/after number should come from T10, not be estimated here.
