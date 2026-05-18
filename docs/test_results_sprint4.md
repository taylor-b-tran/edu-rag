# Sprint 4 31-Query API Test Results

**Project:** EduRAG / Paedia, Group 19, CSIT321
**Prepared by:** Tung Phuong Anh Huynh
**Reviewed and regenerated in sandbox by:** Thanh Binh Tran support workflow
**Sprint task:** Task 15 - 31-query API test evidence
**Run date:** 11 May 2026
**Base commit tested:** `946e665` (`origin/develop`)

## Test Environment

| Item | Value |
|---|---|
| API mode | Flask test client, fixture backend, in-memory state |
| Authentication | `student@uow.edu.au`, role `student`, course `CSIT321` |
| Query corpus | `tests/test_queries.json` |
| Total queries | 31 |
| Rate limit handling | Test harness raised `_RATE_MAX` to 1000 so the full corpus could run in one batch |
| Health endpoint status | HTTP 200 |
| Sessions endpoint status after queries | HTTP 200 |

## Result Summary

| Category | Total | PASS | PARTIAL | FAIL | Strict pass rate | Lenient rate |
|---|---:|---:|---:|---:|---:|---:|
| `easy_factual` | 8 | 0 | 2 | 6 | 0.0% | 25.0% |
| `hard_reasoning` | 12 | 0 | 0 | 12 | 0.0% | 0.0% |
| `off_topic` | 6 | 6 | 0 | 0 | 100.0% | 100.0% |
| `ambiguous` | 5 | 0 | 4 | 1 | 0.0% | 80.0% |
| **Total** | 31 | 6 | 6 | 19 | 19.4% | 38.7% |

Strict pass rate is low because the Sprint 4 API is still running against a small fixture bank, not the live ChromaDB-backed RAG pipeline. This result should be treated as fixture-mode coverage evidence, not production RAG quality.

## Key Findings

- All 31 API calls returned HTTP 200 after the benchmark harness bypassed the per-IP rate limit.
- Off-topic fallback handling is strong: all 6 off-topic queries returned fallback responses.
- In-scope factual and reasoning coverage is weak because the fixture bank has only a few broad answers.
- Several in-scope queries are routed to unrelated SQL or normalisation fixtures, showing that the fuzzy matcher is too permissive for benchmark scoring.
- Q031 should be FAIL, not PASS: it received a SQL joins answer for an ambiguous failure-recovery question.
- Thanh Binh Tran Task 3 should wait for this Task 15 evidence to be accepted before updating the RAG benchmark artifact.

## Per-Query Results

| ID | Category | HTTP | Fallback | Matched fixture | Verdict | Note |
|---|---|---:|---|---|---|---|
| Q001 | `easy_factual` | 200 | no | Can you summarize the key steps in the RAG pipeline? | PARTIAL | On-topic fixture selected but does not fully answer the specific question: Can you summarize the key steps in the RAG pipeline?. |
| Q002 | `easy_factual` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q003 | `easy_factual` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q004 | `easy_factual` | 200 | no | What are SQL joins and when should I use each type? | FAIL | Wrong or incomplete fixture selected: What are SQL joins and when should I use each type?. |
| Q005 | `easy_factual` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q006 | `easy_factual` | 200 | no | What is Retrieval-Augmented Generation and how does it differ from standard LLMs? | PARTIAL | On-topic fixture selected but does not fully answer the specific question: What is Retrieval-Augmented Generation and how does it differ from standard LLMs?. |
| Q007 | `easy_factual` | 200 | no | What are SQL joins and when should I use each type? | FAIL | Wrong or incomplete fixture selected: What are SQL joins and when should I use each type?. |
| Q008 | `easy_factual` | 200 | no | What are SQL joins and when should I use each type? | FAIL | Wrong or incomplete fixture selected: What are SQL joins and when should I use each type?. |
| Q009 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q010 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q011 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q012 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q013 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q014 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q015 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q016 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q017 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q018 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q019 | `hard_reasoning` | 200 | no | Explain normalization in databases | FAIL | Wrong or incomplete fixture selected: Explain normalization in databases. |
| Q020 | `hard_reasoning` | 200 | yes | fallback | FAIL | Fallback returned for an in-scope benchmark query. |
| Q021 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q022 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q023 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q024 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q025 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q026 | `off_topic` | 200 | yes | fallback | PASS | Correct fallback for out-of-scope query. |
| Q027 | `ambiguous` | 200 | yes | fallback | PARTIAL | Fallback is acceptable for ambiguous wording, but a clarification response would be stronger. |
| Q028 | `ambiguous` | 200 | yes | fallback | PARTIAL | Fallback is acceptable for ambiguous wording, but a clarification response would be stronger. |
| Q029 | `ambiguous` | 200 | yes | fallback | PARTIAL | Fallback is acceptable for ambiguous wording, but a clarification response would be stronger. |
| Q030 | `ambiguous` | 200 | yes | fallback | PARTIAL | Fallback is acceptable for ambiguous wording, but a clarification response would be stronger. |
| Q031 | `ambiguous` | 200 | no | What are SQL joins and when should I use each type? | FAIL | Wrong fixture selected: What are SQL joins and when should I use each type?. |

## Follow-Up

- Tung Task 15: keep this report as fixture-mode evidence only unless the team reruns against a live vector store.
- Tung Task 16: sample corpus expansion should not commit raw `data/samples/` binaries unless the team explicitly changes the current ignore policy.
- Thanh Task 3: update `docs/rag_config.md` and the benchmark JSON only after the Task 15 evidence is accepted as current and scoped correctly.

*Prepared for Sprint 4 Task 15 evidence cleanup on 11 May 2026.*
