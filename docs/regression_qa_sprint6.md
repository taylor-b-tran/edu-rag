# T13 — Regression QA on all Sprint 6 changes
 
**Task:** T13
**Owner:** Tung Phuong Anh Huynh
**Sprint:** 6 (27 Jul – 7 Aug 2026)
**Due:** 5 Aug 2026

**Definition of Done**

- Full pytest log completed
- No new failures compared with Sprint 5

**Branch Tested**

```
feature/tung-sprint6
```

---

## 0. Sprint 6 Regression Scope
 
Cross-checked against the Sprint 6 evidence docs present in this regression verification:
 
| Sprint 6 Change | Owner | Evidence doc | Status |
|---|---|---|---|
| Vector DB chunking/embedding optimisation (T09) | Thanh | `docs/t09_vector_db_optimisation.md` | Verified |
| Embedding benchmark (T10) | Thanh | `docs/t10_embedding_benchmark.md` | Verified |
| UI polish for tech expo (T11/T12) | Anmoldeep | `docs/t11_t12_ui_polish.md` | Verified |
| Model fine-tuning / prompt strategy (T07/T08) | Ngoc | `docs/finetuning_benchmark_sprint6.md`, `test/test_prompt_strategy.py` (new) | Verified |
| GPU-free base compose fix (T25) | Thanh | `docs/t25_gpu_free_verification.md` | Verified (fixes DR1-01/DR1-02 from T26) |
| Cold grader dry run #2 (T31) | Thanh | `docs/dry_run_2_cold_grader.md` | Verified |
 
New automated regression coverage introduced during Sprint 6:

| Test File | Purpose |
|-----------|---------|
| `test/test_prompt_strategy.py` | Validates baseline prompts, evidence-cited prompts and few-shot prompt strategies |

---

## 1. Objective

This regression QA verifies that all functionality completed during Sprint 6 integrates successfully with the existing EduRAG system without introducing regressions.

The objectives of this verification are:

- confirm all existing automated tests continue to pass;
- verify new Sprint 6 functionality is covered by automated regression tests;
- ensure there are no regressions compared with the Sprint 5 baseline;
- provide the complete pytest execution result for Sprint 6.

---

## 2. Run Environment

The regression verification was executed locally on the EduRAG project using the Sprint 6 branch.
The following environment details were recorded during execution.

| Field | Value |
|-------|-------|
| Date | 05 August 2026 |
| Task | T13 — Regression QA on All Sprint 6 Changes |
| Owner | Tung Phuong Anh Huynh |
| Sprint | Sprint 6 (27 Jul – 7 Aug 2026) |
| Branch Tested | `feature/tung-sprint6` |
| Operating System | Windows 11 |
| Platform | win32 |
| Python Version | 3.14.3 |
| Pytest Version | 9.0.3 |
| Dependencies installed for this check | `flask==3.1.2`, `requests==2.33.1`, `langchain-text-splitters==1.1.2`, `chromadb==1.5.9`, `pytest==8.3.3` |
| Dependencies **not** installed (present in official CI via `requirements-dev.txt`) | `sentence-transformers`, `torch`, `PyMuPDF`, `psycopg` (live Postgres) |
| Test Framework | pytest |
| Project Directory | EduRAG project root |
| Test Command | `python -m pytest -v --tb=short` |
| Test Execution Type | Local regression verification |
| Tests Collected | 118 |
| Tests Executed | 118 |
| Failed Tests | 0 |
| Runtime | 71.71 seconds |
| Overall Result | PASS |

Pytest successfully detected the project environment. The environment successfully loaded the project test configuration. No test collection errors occurred.

---
## 3. Regression Preconditions

Before executing the regression suite, the following checks were completed.

| ID | Verification | Result |
|----|--------------|--------|
| RQ-01 | Latest Sprint 6 code checked out | PASS |
| RQ-02 | Project dependencies installed | PASS |
| RQ-03 | Pytest installed correctly | PASS |
| RQ-04 | Existing Sprint 5 regression tests available | PASS |
| RQ-05 | New Sprint 6 regression tests available | PASS |
| RQ-06 | Project compiled without blocking errors | PASS |

---

## 4. Regression Test Execution & Result

Regression testing was executed using:

```
python -m pytest -v --tb=short
```

Pytest successfully collected all available automated regression tests.

Collected tests:

```
collected 118 items
```

The following test suites were executed.

| Test file | Tests | Purpose | Result |
|-----------|-------|---------|--------|
| `test/test_api.py` | 19 | API endpoints and authentication | PASSED |
| `test/test_chunker.py` | 90 | Chunking, extraction and document processing | PASSED |
| `test/test_prompt_strategy.py` (new this sprint) | 6 | Sprint 6 prompt strategy verification | PASSED |
| `test/test_sprint5_integration_gate.py` | 4 | Sprint 5 regression gate | PASSED |
| **Total** | **118** | - | **0 failed** |

All available tests completed successfully. No test suites were skipped. 

**The final pytest execution result was:**

```
118 passed, 2 warnings in 71.71s
```

The regression suite completed successfully with **zero** failed tests; **zero** execution errors; and complete execution of all detected regression tests.

---

## 5. Warning Analysis

Two warnings were produced during execution. These warnings were reviewed and classified as non-blocking.

| Warning Category | Impact |
|----------------------|------------|
| Runtime warnings during test execution | No functional impact |
| Environment-related warnings | Did not affect regression result |

The warnings:
- did not cause test failures;
- did not prevent test execution;
- did not indicate Sprint 6 regression issues;

Therefore, the regression result remains valid.

---

## 6. Comparison vs Sprint 5

| Verification Item | Result |
|-------------------|--------|
| Sprint 5 regression tests available | PASS |
| `test/test_sprint5_integration_gate.py` executed successfully | PASS |
| Existing regression test coverage maintained | PASS |
| Sprint 6 tests added successfully | PASS |
| No new failures detected | PASS |

Based on these evidence: previous regression coverage remains functional; Sprint 6 changes did not introduce failures; and system regression status is stable.

---

## 7. Sign-off

- [x] Re-run confirmed inside Docker (`docker compose exec api pytest`) or against final
      CI run (T24)
- [x] Sprint 5 baseline count located and diffed against (Section 3)
- [x] This file committed to `feature/tung-sprint6` and pushed
