# RAG Limitations — Sprint 5
## 1. Retrieval Limits
The seeded corpus covers CSIT321 lecture slides only — tutorial sheets, assignment specs, and external readings are not indexed. Retrieval quality degrades when student phrasing differs from source terminology (vocabulary mismatch), or when queries use unexpanded acronyms (e.g. "RAG" vs "Retrieval-Augmented Generation"). Compound questions are embedded as a single vector, so one part may dominate and the other goes underserved.

Chunks below `SIMILARITY_THRESHOLD` (default 0.30) are discarded entirely, so a query with no strong match returns zero chunks and triggers fallback even if weaker-but-relevant material exists. Only the top `TOP_K` (default 5) chunks are passed to the LLM, meaning broad questions spanning multiple weeks may receive a narrower answer than expected. There is no re-ranking stage — retrieval order is determined purely by cosine similarity.

## 2. Fixture Fallback
Fallback activates when zero chunks pass the similarity threshold. In this state the answer is prefixed with `"Based on general knowledge — not verified against course materials."`, source references are empty, confidence is `"Low"` / `0.0`, and `is_fallback: true` is set in the response. The fallback does not refuse to answer — Ollama still generates from pre-trained weights with no course context, so the response may be generically correct but not aligned to the CSIT321 syllabus. The `is_fallback` flag is the authoritative indicator and must be checked before presenting any answer as ChromaDB-grounded.

If Ollama is unreachable (`ConnectionError`), `_call_ollama` returns a structured error string with the restart instruction and any retrieved chunk summaries rather than raising. The HTTP status remains 200 in this path.

## 3. Remaining Risks
| Risk | Severity | Status |
|------|----------|--------|
| Sparse corpus causes high fallback rate on valid CSIT321 questions | Medium | Mitigated by seeded corpus; coverage gaps unmeasured |
| Embedding model produces low similarity for paraphrased questions | Medium | No re-ranker in scope for Sprint 5 |
| Ollama latency exceeds demo timeout (120 s) | Low–Medium | llama3.2 on CPU can be slow on first load |
| Fixture fallback mistaken for live RAG in demo recording | High | `is_fallback` flag in API JSON; demo script must verify |
| ChromaDB collection empty after Docker restart | Medium | Volume mount required in `docker-compose.yml`; verify before recording |
