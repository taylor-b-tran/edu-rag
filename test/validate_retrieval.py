import os, sys, json, time, textwrap
from typing import List, Dict
from src.document_processor.rag_pipeline import VectorRetriever, LLMResponseGeneration, SIMILARITY_THRESHOLD

DEMO_QUERIES: List[Dict] = [
    {
        "id": "Q01", "category": "Easy Factual",
        "question": "What is Retrieval-Augmented Generation (RAG)?",
        "expected_topic": "RAG Fundamentals",
        "expected_source": "Week1_RAG_Introduction.pdf",
        "expected_keywords": ["retrieval", "generative", "knowledge base", "hallucination"],
        "expect_fallback": False,
    },
    {
        "id": "Q02", "category": "Easy Factual",
        "question": "What embedding model does EduRAG use and what is its dimension?",
        "expected_topic": "Vector Embeddings",
        "expected_source": "Week2_Vector_Embeddings.pdf",
        "expected_keywords": ["all-MiniLM-L6-v2", "384", "SentenceTransformers"],
        "expect_fallback": False,
    },
    {
        "id": "Q03", "category": "Hard Reasoning",
        "question": (
            "Why was ChromaDB chosen over FAISS for EduRAG, and how does course_id "
            "metadata filtering prevent cross-course retrieval leakage?"
        ),
        "expected_topic": "ChromaDB",
        "expected_source": "Week3_ChromaDB_VectorStore.pdf",
        "expected_keywords": ["course_id", "filter", "metadata", "cosine"],
        "expect_fallback": False,
    },
    {
        "id": "Q04", "category": "Applied / Procedural",
        "question": (
            "How does EduRAG handle a student question when no retrieved chunk "
            "exceeds the similarity threshold?"
        ),
        "expected_topic": "RAG Evaluation",
        "expected_source": "Week6_RAG_Evaluation.pdf",
        "expected_keywords": ["fallback", "general knowledge", "threshold", "label"],
        "expect_fallback": False,
    },
    {
        "id": "Q05", "category": "Off-topic / Fallback",
        "question": "What is the best recipe for chocolate cake and how long should I bake it?",
        "expected_topic": "N/A",
        "expected_source": "N/A",
        "expected_keywords": [],
        "expect_fallback": True,
    },
]

W = 68

def wrap(text, indent=4):
    return textwrap.fill(text, width=W, initial_indent=" "*indent, subsequent_indent=" "*indent)

def check_kw(answer, kws):
    found = sum(1 for k in kws if k.lower() in answer.lower())
    return found, len(kws)

def run_validation(use_ollama=True):
    print(f"\n{'='*W}")
    print("  EduRAG -- Retrieval Quality Validation  (S5-T19)")
    print(f"  Queries: {len(DEMO_QUERIES)} | Threshold: {SIMILARITY_THRESHOLD}")
    print(f"{'='*W}\n")

    retriever = VectorRetriever()
    generator = LLMResponseGeneration(retriever=retriever) if use_ollama else None
    results   = []

    for q in DEMO_QUERIES:
        print(f"{'─'*W}")
        print(f"  [{q['id']}] {q['category']}")
        print(f"  Q: {q['question']}\n")

        t0     = time.time()
        chunks = retriever.search(q["question"], top_k=5)
        good   = [c for c in chunks if c.similarity >= SIMILARITY_THRESHOLD]
        is_fb  = len(good) == 0

        print(f"  Retrieval: {len(good)}/{len(chunks)} chunks >= threshold ({SIMILARITY_THRESHOLD})")
        for i, ch in enumerate(good[:3], 1):
            print(f"    {i}. {ch.source_file} p.{ch.page_number} "
                  f"[{ch.topic}] sim={ch.similarity:.3f}")

        answer_text = ""
        confidence  = "Low" if is_fb else (
            "High" if good and good[0].similarity >= 0.60 else "Medium")
        conf_score  = (sum(c.similarity for c in good)/len(good)) if good else 0.0

        if generator and not is_fb:
            try:
                resp        = generator.generate(q["question"])
                answer_text = resp.answer
                confidence  = resp.confidence
                conf_score  = resp.confidence_score
                is_fb       = resp.is_fallback
            except Exception as exc:
                answer_text = f"[Ollama error: {exc}]"
        elif is_fb:
            answer_text = "(fallback -- no chunks above threshold)"
        elif not use_ollama and good:
            answer_text = f"[Retrieval-only] Best: {good[0].text[:250]}..."

        latency_ms = int((time.time() - t0) * 1000)

        expect_fb    = q.get("expect_fallback", False)
        fb_pass      = is_fb == expect_fb
        kw_f, kw_t   = check_kw(answer_text, q["expected_keywords"])
        kw_pass      = kw_t == 0 or (kw_f / kw_t >= 0.5)
        src_hit      = any(q["expected_source"] in c.source_file
                          for c in good) if q["expected_source"] != "N/A" else True
        overall_pass = fb_pass and (kw_pass or expect_fb)

        conf_label = {"High": "[High]", "Medium": "[Med] ", "Low": "[Low] "}.get(confidence, "[---]")
        print(f"\n  Confidence : {conf_label} {confidence} ({conf_score:.3f})")
        print(f"  Fallback   : {'YES' if is_fb else 'NO'} "
              f"(expected {'YES' if expect_fb else 'NO'}) {'PASS' if fb_pass else 'FAIL'}")
        print(f"  Source hit : {'PASS' if src_hit else 'FAIL'}  ({q['expected_source']})")
        if kw_t > 0:
            print(f"  Keywords   : {kw_f}/{kw_t} {'PASS' if kw_pass else 'FAIL'}")
        print(f"  Latency    : {latency_ms} ms")
        if answer_text and len(answer_text) > 10:
            short = answer_text[:280].replace("\n"," ")
            print(f"\n  Preview:\n{wrap(short)}")
        print(f"\n  Result: {'PASS' if overall_pass else 'FAIL'}\n")

        results.append({
            "id": q["id"], "category": q["category"], "question": q["question"],
            "chunks_found": len(good), "source_hit": src_hit,
            "keyword_pass": kw_pass, "fallback_pass": fb_pass,
            "is_fallback": is_fb, "confidence": confidence,
            "conf_score": round(conf_score, 3), "latency_ms": latency_ms,
            "overall_pass": overall_pass,
        })

    passed  = sum(1 for r in results if r["overall_pass"])
    total   = len(results)
    avg_lat = sum(r["latency_ms"] for r in results) / total

    print(f"{'='*W}")
    print("VALIDATION SUMMARY")
    print(f"{'='*W}")
    print(f" Queries: {total}")
    print(f" Passed: {passed} / {total}  ({passed/total*100:.0f}%)")
    print(f" Avg lat: {avg_lat:.0f} ms")
    print(f" Mode: {'Full (Ollama)' if use_ollama else 'Retrieval-only'}")
    print(f"{'='*W}\n")

    rpt = os.path.join(os.path.dirname(__file__), "validation_report.json")
    with open(rpt, "w") as fh:
        json.dump({"results": results, "summary": {
            "total": total, "passed": passed,
            "pass_rate": round(passed/total, 3),
            "avg_latency_ms": round(avg_lat, 1),
            "mode": "full" if use_ollama else "retrieval-only",
        }}, fh, indent=2)
    print(f"Report: {rpt}\n")
    return results

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--no-ollama", action="store_true")
    args = p.parse_args()
    run_validation(use_ollama=not args.no_ollama)
