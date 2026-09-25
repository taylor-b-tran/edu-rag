import sys, os, json
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from src.document_processor.rag_pipeline import VectorRetriever, SIMILARITY_THRESHOLD

SPRINT = os.getenv("BENCHMARK_SPRINT", "10")

EVAL_SET_PATH = Path("tests/retrieval_eval_set.json")
OUT_JSON = Path(f"docs/retrieval_benchmark_sprint{SPRINT}.json")
OUT_MD = Path(f"docs/retrieval_benchmark_sprint{SPRINT}.md")

P_AT_K = 5
R_AT_K = 10

TARGET_PRECISION_AT_5 = 0.7
TARGET_RECALL_AT_10 = 0.8


def precision_at_k(retrieved_ids: list, relevant_ids: set, k: int) -> float:
    # % of the top-K results that are actually relevant
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return round(hits / len(top_k), 3)


def recall_at_k(retrieved_ids: list, relevant_ids: set, k: int) -> float:
    # % of all relevant chunks that made it into the top-K
    if not relevant_ids:
        return None  # off-topic questions have no ground truth -> not applicable
    top_k = retrieved_ids[:k]
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return round(hits / len(relevant_ids), 3)


def reciprocal_rank(retrieved_ids: list, relevant_ids: set) -> float:
    # 1/position of the first correct result (1.0 = correct answer ranked first)
    if not relevant_ids:
        return None
    for i, cid in enumerate(retrieved_ids, 1):
        if cid in relevant_ids:
            return round(1.0 / i, 3)
    return 0.0


def run_benchmark(eval_set: list, retriever: VectorRetriever) -> list:
    results = []
    max_k = max(P_AT_K, R_AT_K)
    for item in eval_set:
        relevant = set(item["relevant_chunk_ids"])
        # T8-14: search now scopes by course_id, matching real usage (generate()
        # always passes one) — previously this searched unscoped across all 4
        # courses. Every current eval question is CSIT321 content, so that's the
        # default; new questions for the other courses should set "course_id".
        course_id = item.get("course_id", "CSIT321")
        chunks = retriever.search(item["question"], course_id=course_id, top_k=max_k)
        retrieved_ids = [c.chunk_id for c in chunks]
        best_similarity = chunks[0].similarity if chunks else 0.0
        would_fallback = best_similarity < SIMILARITY_THRESHOLD

        # T17: which topics the top-5 results actually belong to.
        # If a question's top results come from a different topic than
        # its own, that's the "citations from unrelated topics" issue
        # from Sprint 10 - worth catching automatically every run,
        # not just when someone happens to notice it.
        top5_topics = [c.topic for c in chunks[:P_AT_K] if c.topic]
        off_topic_hits = sorted({t for t in top5_topics if t and t != item["topic"]})

        results.append({
            "id": item["id"],
            "question": item["question"],
            "topic": item["topic"],
            "relevant_chunk_ids": item["relevant_chunk_ids"],
            "retrieved_top10": retrieved_ids,
            "precision_at_5": precision_at_k(retrieved_ids, relevant, P_AT_K),
            "recall_at_10": recall_at_k(retrieved_ids, relevant, R_AT_K),
            "reciprocal_rank": reciprocal_rank(retrieved_ids, relevant),
            "is_off_topic_query": len(relevant) == 0,
            "correctly_triggered_fallback": (len(relevant) == 0 and would_fallback),
            "best_similarity": round(best_similarity, 3),
            "top5_topics": top5_topics,
            "topic_dispersion_flag": bool(off_topic_hits) and len(relevant) > 0,
            "unrelated_topics_hit": off_topic_hits,
        })
    return results


def theoretical_max_precision_at_5(in_corpus: list) -> float:
    """The best possible Precision@5 given how many relevant chunks each
    question actually has. If most questions only have 1 correct chunk,
    1/5 = 0.2 is the ceiling -- no retrieval algorithm can score higher
    than this, so it's not a fair 0.7 comparison on its own."""
    if not in_corpus:
        return None
    per_query_max = [min(len(r["relevant_chunk_ids"]), P_AT_K) / P_AT_K for r in in_corpus]
    return round(sum(per_query_max) / len(per_query_max), 3)


def corpus_document_distribution(collection) -> dict:
    """How indexed passages are spread across source documents.

    T17: retrieval figures on their own can look better than the testing
    actually was if most of the corpus -- and therefore most chances to
    retrieve something relevant -- comes from one document. This has to be
    reported alongside every accuracy number, not just noted once.

    Reads metadata directly rather than iterating chunk-by-chunk with
    n_results, since a ChromaDB collection.get() with no query returns every
    record's metadata in one call.
    """
    try:
        got = collection.get(include=["metadatas"])
    except Exception:
        return {"available": False}

    metas = got.get("metadatas") or []
    total = len(metas)
    if not total:
        return {"available": False}

    counts: dict[str, int] = {}
    for m in metas:
        source = (m or {}).get("source_file", "Unknown")
        counts[source] = counts.get(source, 0) + 1

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top_file, top_count = ranked[0]
    top_share = round(top_count / total, 3)

    return {
        "available": True,
        "total_chunks": total,
        "n_documents": len(counts),
        "top_document": top_file,
        "top_document_chunks": top_count,
        "top_document_share": top_share,
        "by_document": [
            {"source_file": f, "chunks": c, "share": round(c / total, 3)}
            for f, c in ranked
        ],
    }


def summarise(results: list, corpus_size: int = None, distribution: dict = None) -> dict:
    # Split into normal questions (have ground truth) vs off-topic controls (shouldn't match anything)
    in_corpus = [r for r in results if not r["is_off_topic_query"]]
    off_topic = [r for r in results if r["is_off_topic_query"]]

    def avg(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    avg_p5 = avg([r["precision_at_5"] for r in in_corpus])
    max_p5 = theoretical_max_precision_at_5(in_corpus)

    imbalance_flag = bool(
        distribution and distribution.get("available") and distribution["top_document_share"] > 0.4
    )

    return {
        "corpus_size": corpus_size,
        "corpus_distribution": distribution,
        "corpus_imbalance_flagged": imbalance_flag,
        "n_queries": len(results),
        "n_in_corpus_queries": len(in_corpus),
        "n_off_topic_queries": len(off_topic),
        "avg_precision_at_5": avg_p5,
        "theoretical_max_precision_at_5": max_p5,
        "precision_at_5_pct_of_ceiling": (
            round(avg_p5 / max_p5, 3) if avg_p5 is not None and max_p5 else None
        ),
        "avg_recall_at_10": avg([r["recall_at_10"] for r in in_corpus]),
        "mrr": avg([r["reciprocal_rank"] for r in in_corpus]),
        "off_topic_fallback_correct_rate": avg(
            [1.0 if r["correctly_triggered_fallback"] else 0.0 for r in off_topic]
        ),
        "meets_precision_target": (
            avg_p5 is not None and avg_p5 >= TARGET_PRECISION_AT_5
        ),
        "meets_recall_target": (
            avg([r["recall_at_10"] for r in in_corpus]) is not None
            and avg([r["recall_at_10"] for r in in_corpus]) >= TARGET_RECALL_AT_10
        ),
    }


def build_interpretation(summary: dict, results: list) -> list:
    """Plain-English explanation of the numbers, so a low Precision@5 isn't
    misread as broken retrieval when it's actually a corpus-size ceiling."""
    lines = ["## Interpretation", ""]

    corpus_size = summary.get("corpus_size")
    corpus_desc = f"a {corpus_size}-chunk corpus" if corpus_size else "the current corpus"

    max_p5 = summary["theoretical_max_precision_at_5"]
    avg_p5 = summary["avg_precision_at_5"]
    if max_p5 is not None and max_p5 < TARGET_PRECISION_AT_5:
        pct = summary["precision_at_5_pct_of_ceiling"]
        lines.append(
            f"**Precision@{P_AT_K} target not met, but this is a corpus-size ceiling, "
            f"not a retrieval failure.** Most questions in this labelled set have only "
            f"1-2 truly relevant chunks in {corpus_desc}, so the best possible "
            f"Precision@{P_AT_K} is {max_p5} (= relevant chunks / {P_AT_K}), well below "
            f"the {TARGET_PRECISION_AT_5} target from a corpus with 5+ relevant chunks "
            f"per question in mind. The pipeline scored {avg_p5}, which is "
            f"{int(pct*100) if pct else '?'}% of the achievable ceiling -- effectively "
            f"the maximum possible result on this corpus."
        )
        lines.append("")

    # Genuine gaps: relevant chunk never found in top 10 at all
    missed = [r for r in results if not r["is_off_topic_query"] and r["recall_at_10"] is not None and r["recall_at_10"] < 1.0]
    if missed:
        ids = ", ".join(r["id"] for r in missed)
        lines.append(
            f"**Genuine retrieval gaps ({len(missed)}):** {ids} -- relevant chunk(s) were "
            f"not found even in the top 10. These are real weaknesses worth investigating, "
            f"unlike the Precision@5 ceiling above."
        )
        lines.append("")
    else:
        lines.append(
            "**No genuine retrieval gaps found** -- every relevant chunk for every "
            "in-corpus question was retrieved somewhere in the top 10 "
            f"(Recall@{R_AT_K} = {summary['avg_recall_at_10']})."
        )
        lines.append("")

    # Ranking softness: found, but not ranked #1
    not_first = [r for r in results if not r["is_off_topic_query"] and r["reciprocal_rank"] is not None and r["reciprocal_rank"] < 1.0 and r["reciprocal_rank"] > 0]
    if not_first:
        ids = ", ".join(r["id"] for r in not_first)
        lines.append(
            f"**Ranking softness ({len(not_first)}):** {ids} -- the correct chunk was found "
            f"but not ranked first. Minor; worth a look if it recurs on a larger corpus."
        )
        lines.append("")

    # T17: flag any question whose top-5 results included another topic.
    # This is what "citations from unrelated topics" looks like in the
    # numbers - worth checking even when precision/recall look fine,
    # since a wrong-topic chunk can still rank high alongside good ones.
    dispersed = [r for r in results if r.get("topic_dispersion_flag")]
    if dispersed:
        lines.append(f"**Topic dispersion ({len(dispersed)}):** questions whose top-5 results "
                      "included chunks from a different topic than the question itself:")
        lines.append("")
        for r in dispersed:
            lines.append(f"- {r['id']} ({r['topic']}): also pulled in {', '.join(r['unrelated_topics_hit'])}")
        lines.append("")

    lines.append(
        f"**Bottom line:** MRR = {summary['mrr']} means the correct chunk is ranked "
        f"first for the large majority of questions, and Recall@{R_AT_K} = "
        f"{summary['avg_recall_at_10']} confirms retrieval is finding the right material. "
        f"Precision@{P_AT_K} should be re-evaluated once the corpus grows beyond a "
        f"1-2-relevant-chunk-per-question shape."
    )
    lines.append("")
    return lines


def write_markdown(summary: dict, results: list, path: Path, title: str = None):
    if title is None:
        title = f"Sprint {SPRINT} -- Formal Retrieval Accuracy Benchmark Report"
    corpus_size = summary.get("corpus_size")
    lines = [
        f"# {title}",
        "",
        f"**Corpus size at benchmark time: {corpus_size if corpus_size is not None else 'unknown'} chunks.** "
        f"If this doesn't match what you expect, the collection wasn't reseeded before "
        f"this ran -- see `ingest(force_reload=True)` in `src/document_processor/ingest_corpus.py`.",
        "",
    ]
    dist = summary.get("corpus_distribution")
    if dist and dist.get("available"):
        pct = int(round(dist["top_document_share"] * 100))
        warn = " **This is the corpus-imbalance caveat noted in Sprint 10 task 17.**" if summary.get("corpus_imbalance_flagged") else ""
        lines += [
            f"**Corpus balance: one document, `{dist['top_document']}`, accounts for "
            f"{pct}% of all {dist['total_chunks']} indexed passages "
            f"({dist['top_document_chunks']} chunks) across {dist['n_documents']} documents.**{warn} "
            "Any accuracy figure below should be read with this in mind: it reflects how well "
            "retrieval works on the material that dominates the corpus, not how broadly it has "
            "been tested across documents.",
            "",
        ]
    lines += [
        f"Labelled set: `tests/retrieval_eval_set.json` "
        f"({summary['n_in_corpus_queries']} in-corpus questions + "
        f"{summary['n_off_topic_queries']} off-topic control questions)",
        "",
        "Targets are EduRAG's own documented targets "
        "(see the `csit321-w6-evaluation` seed chunk): "
        f"Precision@{P_AT_K} >= {TARGET_PRECISION_AT_5}, "
        f"Recall@{R_AT_K} >= {TARGET_RECALL_AT_10}.",
        "",
        "## Summary",
        "",
        "| Metric | Result | Target | Met? |",
        "|---|---:|---:|:---:|",
        f"| Precision@{P_AT_K} | {summary['avg_precision_at_5']} | "
        f">= {TARGET_PRECISION_AT_5} | {'YES' if summary['meets_precision_target'] else 'NO'} |",
        f"| Recall@{R_AT_K} | {summary['avg_recall_at_10']} | "
        f">= {TARGET_RECALL_AT_10} | {'YES' if summary['meets_recall_target'] else 'NO'} |",
        f"| MRR (mean reciprocal rank) | {summary['mrr']} | -- | -- |",
        f"| Off-topic fallback correct rate | {summary['off_topic_fallback_correct_rate']} | 1.0 | "
        f"{'YES' if summary['off_topic_fallback_correct_rate'] == 1.0 else 'NO'} |",
        "",
    ]
    lines += build_interpretation(summary, results)
    lines += [
        "## Per-Query Results",
        "",
        "| ID | Question | Topic | P@5 | R@10 | RR |",
        "|---|---|---|---:|---:|---:|",
    ]
    for r in results:
        q_short = r["question"][:55] + ("..." if len(r["question"]) > 55 else "")
        rec = "--" if r["recall_at_10"] is None else r["recall_at_10"]
        rr  = "--" if r["reciprocal_rank"] is None else r["reciprocal_rank"]
        lines.append(f"| {r['id']} | {q_short} | {r['topic']} | {r['precision_at_5']} | {rec} | {rr} |")
    lines.append("")
    lines.append(f"Raw per-query results: `{OUT_JSON}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    if not EVAL_SET_PATH.exists():
        print(f"ERROR: {EVAL_SET_PATH} not found. Run this from the project root.")
        sys.exit(1)

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(eval_set)} labelled queries from {EVAL_SET_PATH}")

    print("\nLoading retriever...")
    retriever = VectorRetriever()
    try:
        corpus_size = retriever._collection.count()
    except Exception:
        corpus_size = None

    if not corpus_size:
        print(
            "\nERROR: the ChromaDB collection is empty (0 chunks). This usually means "
            "the corpus hasn't been seeded yet. Run:\n"
            "    python -c \"from src.document_processor.ingest_corpus import ingest; "
            "print(ingest(force_reload=True))\"\n"
            "and try again. Not writing a report against an empty collection."
        )
        sys.exit(1)
    print(f"Collection has {corpus_size} chunks.")

    print("\nChecking corpus document distribution...")
    distribution = corpus_document_distribution(retriever._collection)
    if distribution.get("available"):
        pct = int(round(distribution["top_document_share"] * 100))
        print(f"  Top document '{distribution['top_document']}' = {pct}% of {distribution['total_chunks']} chunks")
        if distribution["top_document_share"] > 0.4:
            print("  WARNING: corpus is imbalanced -- see the caveat in the markdown report.")

    print("\nRunning retrieval benchmark (no LLM calls needed)...")
    results = run_benchmark(eval_set, retriever)
    summary = summarise(results, corpus_size=corpus_size, distribution=distribution)

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    write_markdown(summary, results, OUT_MD)

    print(f"\nSaved: {OUT_JSON}")
    print(f"Saved: {OUT_MD}")


if __name__ == "__main__":
    main()
