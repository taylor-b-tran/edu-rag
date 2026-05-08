# EduRAG Sprint 3 RAG Configuration Benchmark

Owner: Thanh Binh Tran  
Project: Paedia EduRAG, CSIT321 Project 37, Group 19  
Batch: Sprint 3 Batch 7  
Date: 22 April 2026  
Status: Provisional Sprint 3 defaults selected

## 1. Purpose

This document records the first Sprint 3 RAG configuration benchmark for Paedia. The goal is not to complete a full academic retrieval evaluation yet. The goal is to choose practical, evidence-based defaults for Sprint 3 integration so later work can proceed with a stable chunking, retrieval, and fallback configuration.

This file also satisfies Ngoc's Sprint 3 Task 14 expectation from the shared Sprint 3 Google Doc: a section titled `Retrieval Edge Cases` must be added to `docs/rag_config.md`.

Raw benchmark evidence is stored in:

`docs/rag_config_benchmark_2026-04-22.json`

## 2. Benchmark Scope

| Item | Value |
|---|---|
| Source document | `materials/book_embNLP_draft.pdf` |
| PDF extraction library | PyMuPDF (`fitz`), matching the Assessment 2 Module 1 parser dependency |
| Pages with extracted text | 163 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Chunking unit | Characters, page-scoped recursive splitting |
| Tested chunk sizes | 256, 512, 1024 |
| Tested overlaps | 0, 50, 100 |
| Tested top-k values | 3, 5, 10 |
| Query set | 3 in-scope questions, 1 out-of-scope fallback question |
| Evaluation style | Heuristic keyword-hit coverage plus distance separation |
| Shared Sprint 3 context checked | Google Doc `Sprint 3 - EduRAG`, including Binh Task 5, Ngoc Task 14, and Tung Task 17 notes |

Tung's Sprint 3 task plan states that a larger 31-question labelled corpus should be prepared with easy factual, hard reasoning, off-topic, and ambiguous categories. That corpus was not present in the local workspace at the time of this Batch 7 run, so this benchmark uses a smaller provisional query set and should be rerun once `tests/test_queries.json` is available.

## 3. Selected Sprint 3 Defaults

| Setting | Provisional Default | Reason |
|---|---:|---|
| Chunk size | 1024 characters | Best separation between in-scope and out-of-scope queries while producing fewer chunks. |
| Chunk overlap | 0 characters | Overlap did not improve coverage on this PDF benchmark and slightly reduced distance separation. |
| PDF extractor | PyMuPDF (`fitz`) | Matches the Assessment 2 report dependency and keeps page-aware extraction before chunking. |
| Retrieval top-k | 5 | Top-3 already worked, but top-5 gives the LLM more context without overloading the prompt. |
| Similarity fallback threshold | 0.65 cosine distance | Separates the hardest in-scope query from the out-of-scope query for the selected config. |
| Embedding model | `all-MiniLM-L6-v2` | Already validated in Batch 5 and suitable for local Sprint 3 hardware. |
| Vector database | ChromaDB | Matches Assessment 2 architecture and supports metadata-filtered retrieval by `course_id`. |
| Generation model | `qwen3:14b` via Ollama | Selected in the hardware/model pass and validated locally with GPU support. |

Important implementation note: PDF text extraction uses PyMuPDF (`fitz`) to match the Assessment 2 documented parser path. The chunk sizes are still character-based for Sprint 3 because the available teammate chunker implementation uses `RecursiveCharacterTextSplitter`-style character limits. If the team later switches to token-based splitting, these values must be re-benchmarked.

Runnable notebook alignment check: after the PyMuPDF update, `notebooks/rag_poc.ipynb` now uses PyMuPDF for PDF extraction and LangChain `RecursiveCharacterTextSplitter` for chunking. A local extraction/chunking check against `materials/book_embNLP_draft.pdf` found 163 text pages and created 466 page-scoped chunks. The retrieval-distance values in this document remain provisional Sprint 3 benchmark evidence and should be refreshed when the larger labelled query set is available.

## 4. Benchmark Results

| Chunk Size | Overlap | Chunks | Top-3 Coverage | Top-5 Coverage | Top-10 Coverage | Avg In-Scope Best Distance | Hardest In-Scope Distance | Out-of-Scope Distance | Separation Margin |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 0 | 1689 | 1.00 | 1.00 | 1.00 | 0.2673 | 0.3068 | 0.6036 | 0.3363 |
| 256 | 50 | 1689 | 1.00 | 1.00 | 1.00 | 0.2607 | 0.2883 | 0.6479 | 0.3872 |
| 256 | 100 | 1689 | 1.00 | 1.00 | 1.00 | 0.2788 | 0.3426 | 0.6479 | 0.3691 |
| 512 | 0 | 846 | 1.00 | 1.00 | 1.00 | 0.2846 | 0.2994 | 0.7258 | 0.4412 |
| 512 | 50 | 846 | 1.00 | 1.00 | 1.00 | 0.2846 | 0.2994 | 0.7477 | 0.4631 |
| 512 | 100 | 846 | 1.00 | 1.00 | 1.00 | 0.2846 | 0.2994 | 0.7584 | 0.4738 |
| 1024 | 0 | 454 | 1.00 | 1.00 | 1.00 | 0.2974 | 0.3232 | 0.8341 | 0.5367 |
| 1024 | 50 | 454 | 1.00 | 1.00 | 1.00 | 0.3118 | 0.3520 | 0.8341 | 0.5223 |
| 1024 | 100 | 454 | 1.00 | 1.00 | 1.00 | 0.3118 | 0.3520 | 0.8341 | 0.5223 |

Lower cosine distance means a closer semantic match. Every configuration retrieved a keyword-relevant result within top-5 for the three in-scope questions. The selected `1024/0` configuration is preferred because it keeps perfect top-k coverage, produces the smallest chunk set, and gives the clearest distance separation from the out-of-scope query.

## 5. Threshold Selection

For the selected `1024/0` configuration:

| Query | Type | Best Distance | Top-3 Evidence |
|---|---|---:|---|
| Q1: word embeddings and usefulness in NLP | In scope | 0.2849 | p47 d=0.2849, p2 d=0.2992, p13 d=0.3187 |
| Q2: static vs contextualized embeddings | In scope | 0.2842 | p81 d=0.2842, p88 d=0.3322, p80 d=0.3447 |
| Q3: sentence and document embeddings | In scope | 0.3232 | p113 d=0.3232, p15 d=0.3482, p110 d=0.3520 |
| Q4: weather in Sydney tomorrow | Out of scope | 0.8341 | p108 d=0.8341, p47 d=0.8459, p110 d=0.8664 |

| Threshold | Correct In-Scope Answers | Correct Fallbacks | False Fallbacks | False Accepts |
|---:|---:|---:|---:|---:|
| 0.55 | 3 | 1 | 0 | 0 |
| 0.60 | 3 | 1 | 0 | 0 |
| 0.65 | 3 | 1 | 0 | 0 |
| 0.70 | 3 | 1 | 0 | 0 |
| 0.75 | 3 | 1 | 0 | 0 |
| 0.80 | 3 | 1 | 0 | 0 |
| 0.85 | 3 | 0 | 0 | 1 |

Recommended Sprint 3 threshold: `0.65`.

This threshold is intentionally conservative. It sits above the hardest in-scope match (`0.3232`) and below the out-of-scope match (`0.8341`). It should be treated as a provisional PDF benchmark value, not a universal production value.

## 6. Teammate Edge-Case Notes Merged

Thi Hong Ngoc Nguyen's extracted Sprint 3 contribution includes a chunker and tests covering the following cases:

| Edge Case | What It Means For RAG Config |
|---|---|
| Empty or whitespace-only text | The ingestion pipeline should skip empty chunks instead of storing meaningless vectors. |
| Very short text | Short pages or snippets should remain one chunk to avoid unnecessary fragmentation. |
| Long English text | Chunking must enforce the configured size limit and avoid empty chunks. |
| Overlap validation | Overlap must be lower than chunk size; invalid values should raise a clear error. |
| Code blocks | Chunking should preserve indentation-sensitive content enough for retrieval. |
| Non-English and mixed-language text | Unicode text should not crash the chunker, even though Sprint 3 does not prioritise multilingual UI. |
| Real PDF text | PyMuPDF page-scoped PDF extraction remains the baseline ingestion path for this Sprint 3 PoC. |

Ngoc's original chunker used `512/50`. This benchmark does not reject that earlier work; it narrows the first integration default for Binh's current PDF-based PoC to `1024/0`. The runtime chunker has since been aligned to `1024/0` so the code, report, and Sprint 3 benchmark use the same baseline.

## 7. Retrieval Edge Cases

This section is included because the shared Sprint 3 Google Doc assigns Ngoc a retrieval-edge-case design task and names this file as the expected destination.

| Edge Case | Detection Rule | System Behaviour | Notes For Sprint 4 |
|---|---|---|---|
| No chunks match above threshold | No retrieved chunk has cosine distance `<= 0.65` after `course_id` filtering. | Do not generate a course answer. Return the approved fallback label: `I could not verify an answer from the available course materials`, or ask the student to upload/check course material depending on UI context. | This prevents unsupported answers when retrieval fails. |
| Borderline similarity | Best distance is close to threshold, recommended watch zone `0.60 < distance <= 0.65`. | Generate an answer only if the answer can cite at least one retrieved source. Use cautious wording such as `The available material suggests...`. | Log borderline cases for later manual review and threshold tuning. |
| Nonsense query | Query is empty, mostly symbols, extremely short, or produces no meaningful semantic match. | Ask the student to rephrase the question instead of sending weak context to the LLM. | Add input validation before retrieval in the Streamlit/API layer. |
| Off-topic from any course | Query is valid language but unrelated to the indexed course corpus, such as weather, news, or unrelated personal advice. | Trigger fallback and clearly state that the answer is not grounded in course materials. | This matches the off-topic category planned for Tung's labelled query corpus. |
| Cross-course leakage risk | Retrieved chunks belong to a different `course_id`, or metadata filtering is absent. | Block the response and log an audit event; retrieval must always filter by `course_id`. | Supervisor feedback in Sprint 3 highlights course-level data isolation as a key differentiator. |
| LLM unavailable after valid retrieval | Retrieval succeeds, but Ollama or the model endpoint fails. | Return a friendly service-unavailable message and preserve retrieved citations for retry/debugging. | Also relevant to Namaratne's DFD error-path work. |

## 8. Suggested Runtime Configuration

```python
RAG_CONFIG = {
    "pdf_extractor": "PyMuPDF (fitz)",
    "chunk_size": 1024,
    "chunk_overlap": 0,
    "top_k": 5,
    "similarity_distance_threshold": 0.65,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "vector_store": "ChromaDB",
    "metadata_filters": ["course_id"],
}
```

Expected retrieval behaviour:

1. Filter vectors by `course_id`.
2. Retrieve top-5 chunks using cosine distance.
3. If no retrieved chunk has distance `<= 0.65`, return the approved fallback label instead of generating an unsupported course answer.
4. If at least one retrieved chunk passes the threshold, generate an evidence-cited answer using the Batch 6 safety-first prompt strategy.

## 9. Known Limitations

This benchmark is useful for Sprint 3 integration, but it is not final evaluation evidence for the whole project.

Current limitations:

- Only one PDF was benchmarked.
- The query set is small and manually chosen.
- Relevance was approximated using keyword-hit coverage and distance separation.
- The PyMuPDF extraction update was source-checked and chunk-count checked; full retrieval-distance results should be rerun with the final labelled corpus.
- PPTX and DOCX parsing were not benchmarked in this batch.
- Hybrid search and reranking were intentionally left out of Sprint 3 Batch 7 scope.

Recommended next evaluation step:

Create a labelled set of 20-30 course-specific questions, then measure `Precision@5`, `Recall@10`, fallback accuracy, answer citation quality, and latency.

## 10. Handoff

This document unblocks Sprint 4 implementation by giving Tai and the backend integration work a stable default configuration. If future batches add PPTX/DOCX ingestion, hybrid retrieval, reranking, or OpenAI fallback models, those changes should be added as new benchmark rows rather than silently replacing this Sprint 3 baseline.
