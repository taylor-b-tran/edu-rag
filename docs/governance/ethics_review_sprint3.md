# Ethics Review - Sprint 3 RAG PoC

## 1. Review Scope

This review examines the Sprint 3 EduRAG proof of concept from an ethics and responsible-use perspective. The focus is not on generic AI risk in the abstract. Instead, it reviews the current RAG PoC design, the available evaluation assets, and the kinds of student-facing answer failures that could occur when the system is used as a course assistant.

The main ethical question for Sprint 3 is whether the prototype can support grounded, transparent study help without misleading students about answer quality, source coverage, or scope.

## 2. Evidence Reviewed

The review is based on the following Sprint 3 artifacts:

- `notebooks/rag_poc.ipynb`
- `docs/rag_config.md`
- `docs/prompt_strategy.md`
- `docs/ollama_model_selection.md`
- `docs/meetings/sprint3_internal_demo.md`
- `Team_Contributions/Tung Phuong Anh Huynh/sprint3_extracted/test_queries.json`
- `Team_Contributions/Tung Phuong Anh Huynh/sprint3_extracted/sample_manifest.md`
- `Team_Contributions/Namaratne/docs/risk_register_sprint3.md`
- `Team_Contributions/Anmoldeep Singh/docs/ui_state.md`

These artifacts show that the Sprint 3 PoC already uses course-scoped retrieval, source references, a fallback label, and a draft confidence scheme. They also show that evaluation is still provisional because the larger labelled query corpus was not fully used during the first benchmark pass.

## 3. Ethical Risk Summary

The Sprint 3 PoC addresses a legitimate educational need, but it also creates risks if students assume every answer is fully accurate, fully sourced, or appropriate for all question types.

The highest ethical risks at this stage are:

- hallucinated or weakly grounded answers when retrieval is poor
- misleading confidence or overly authoritative tone
- off-topic answers that look course-approved when they are not
- ambiguous questions that need clarification rather than a confident answer
- privacy exposure from stored question history and audit data
- cross-course leakage if retrieval filtering fails
- over-reliance by students who may stop checking the underlying source material

## 4. Sample Answer Review

The notebook and prompt/config documents show the intended behaviour, while `test_queries.json` gives a stronger evaluation corpus covering in-scope, off-topic, and ambiguous questions. Some rows below describe observed Sprint 3 behaviour from the notebook evidence, while others describe expected behaviour from the reviewed test assets and design rules.

| Query category | Example question | Observed or expected issue | Risk level | Mitigation | Sprint 4 owner |
|---|---|---|---|---|---|
| Hallucination with weak retrieval | `What is the capital of France?` | Expected issue: an unrelated question could still receive a fluent answer from model prior knowledge if threshold and fallback logic are not enforced strictly. | High | Keep `course_id` filtering, apply similarity threshold, and show the approved fallback label instead of presenting the answer as course-grounded. | Binh / backend integration |
| Thin-source confidence | `What are sentence and document embeddings?` | Observed/expected issue: a plausible answer may be returned from only one or two chunks, which can look more certain than the evidence really is. | High | Tie confidence labels to retrieval signals, not model tone alone, and surface sources beside the answer. | Binh / UI integration |
| Off-topic queries | `Write me a poem about software engineering.` | Expected issue: the assistant may be tempted to comply even though the project scope is course-grounded study support only. | Medium | Reject or label unsupported requests and remind users that EduRAG answers from course materials. | Binh |
| Ambiguous course questions | `How does the system work?` | Expected issue: the question could refer to the full architecture, the upload pipeline, or the query path, creating a risk of answering the wrong thing confidently. | Medium | Ask a clarifying question or provide a clearly labelled high-level overview before going deeper. | Binh / UI integration |
| Bias from sources or model priors | `Why was ChromaDB chosen over FAISS?` | Expected issue: the answer may over-favour prior assumptions or incomplete local evidence if the retrieved material is narrow. | Medium | Cite sources, distinguish design rationale from benchmark proof, and avoid presenting preferences as objective fact without evidence. | Team review |
| Privacy from stored history | `What is a vector embedding?` asked in a named student session | Observed/expected issue: even harmless study questions become identifiable if stored with account and session metadata longer than needed. | Medium | Limit retained metadata, document retention by category, and restrict access by role. | Tai / backend integration |
| Cross-course leakage | `How does the system ensure Course A does not retrieve Course B content?` | Expected issue: if `course_id` filters are missing or bypassed, a student could receive another course's material without realising it. | High | Enforce `course_id` metadata filtering at retrieval time and log violations or blocked events. | Backend integration |
| Student over-reliance | `Explain word embeddings` with a short answer and citations | Observed/expected issue: a concise answer can still encourage students to stop reading the actual lecture material. | Medium | Keep citations visible, encourage source checking, and present the tool as study support rather than an authoritative replacement for course content. | UI / team policy |

## 5. Mitigation Plan

The reviewed artifacts already point to a consistent mitigation strategy:

- use RAG over curated course materials instead of unrestricted answering
- scope retrieval by `course_id` to reduce cross-course leakage
- attach source references to grounded answers
- use a visible fallback label when no sufficiently relevant course chunks are found
- avoid exposing hidden prompts or obeying prompt-injection content
- treat confidence as a backend-supported signal, not a stylistic model claim
- keep test cases for off-topic, ambiguous, and reliability scenarios in the labelled query set

Important limitation: some controls, such as confidence bands and broader moderation behaviour, are documented as intended Sprint 3 or Sprint 4 design choices. They should not be described as fully completed production safeguards unless they are verified in the implemented runtime.

## 6. Requirement And Design Links

This ethics review aligns with the wider Sprint 3 design in the following ways:

- `docs/prompt_strategy.md` defines grounded answering, citations, fallback wording, and prompt-injection resistance.
- `docs/rag_config.md` defines a provisional similarity threshold and emphasises fallback when no chunk passes the threshold.
- `notebooks/rag_poc.ipynb` demonstrates a working local RAG flow over course material and includes a fallback path for off-topic behaviour.
- `Team_Contributions/Tung Phuong Anh Huynh/sprint3_extracted/test_queries.json` expands the evaluation scope beyond a small notebook-only demo.
- `Team_Contributions/Namaratne/docs/risk_register_sprint3.md` identifies hallucination, parsing failure, indexing failure, and cross-course leakage as active risks.
- `Team_Contributions/Anmoldeep Singh/docs/ui_state.md` shows the intended user-facing controls around authentication, role separation, and visible fallback behaviour.

## 7. Sprint 4 Follow-Up Actions

- Run the labelled query set against the implemented pipeline and record actual outputs, not only expected ones.
- Review a representative sample of answers for citation quality, fallback correctness, and ambiguity handling.
- Confirm whether confidence labels are set from retrieval evidence in the backend.
- Add explicit UI wording that EduRAG supports study and revision but does not replace reading the source material.
- Validate privacy retention and audit access decisions before wider testing.
- Document any known gaps between the notebook PoC, Streamlit prototype, and future API implementation.
