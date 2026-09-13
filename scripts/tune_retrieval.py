import sys, os, json
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from src.document_processor.rag_pipeline import VectorRetriever, SIMILARITY_THRESHOLD
from scripts.benchmark_retrieval import precision_at_k, recall_at_k, reciprocal_rank, P_AT_K, R_AT_K

EVAL_SET_PATH = Path("tests/retrieval_eval_set.json")
OUT_JSON = Path("docs/retrieval_tuning_sprint9.json")
OUT_MD = Path("docs/retrieval_tuning_sprint9.md")
SPRINT7_BASELINE = Path("docs/retrieval_benchmark_sprint7.json")

RETRIEVE_K = 10  # matches max(P_AT_K, R_AT_K) in benchmark_retrieval.py

# Candidate thresholds to test, bracketing the current production default
# (SIMILARITY_THRESHOLD in ingest_corpus.py) in both directions.
THRESHOLD_CANDIDATES = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]


def run_queries(eval_set: list, retriever: VectorRetriever, k: int = RETRIEVE_K) -> list:
    """One retrieval pass per query. Everything below (ranking metrics AND
    the threshold sweep) is computed from this list without hitting the
    retriever again."""
    runs = []
    for item in eval_set:
        relevant = item["relevant_chunk_ids"]
        course_id = item.get("course_id", "CSIT321")
        chunks = retriever.search(item["question"], course_id=course_id, top_k=k)
        runs.append({
            "id": item["id"],
            "question": item["question"],
            "is_off_topic": len(relevant) == 0,
            "relevant_chunk_ids": relevant,
            "retrieved_ids": [c.chunk_id for c in chunks],
            "best_similarity": round(chunks[0].similarity, 3) if chunks else 0.0,
        })
    return runs


def ranking_metrics(runs: list) -> dict:
    """P@5 / R@10 / MRR, averaged over the in-corpus queries. Threshold-
    independent -- this is the direct "re-run the Sprint 7 benchmark"
    number, kept here too so the tuning report can quote it next to the
    threshold recommendation without opening a second file."""
    in_corpus = [r for r in runs if not r["is_off_topic"]]
    precisions, recalls, rrs = [], [], []
    for r in in_corpus:
        relevant = set(r["relevant_chunk_ids"])
        precisions.append(precision_at_k(r["retrieved_ids"], relevant, P_AT_K))
        rec = recall_at_k(r["retrieved_ids"], relevant, R_AT_K)
        if rec is not None:
            recalls.append(rec)
        rr = reciprocal_rank(r["retrieved_ids"], relevant)
        if rr is not None:
            rrs.append(rr)

    def avg(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    return {
        "avg_precision_at_5": avg(precisions),
        "avg_recall_at_10": avg(recalls),
        "mrr": avg(rrs),
    }


def threshold_row(runs: list, threshold: float) -> dict:
    """For one candidate threshold: how many real questions would wrongly
    fall back to general knowledge (false fallback), and how many off-topic
    questions correctly do (correct fallback) / incorrectly don't (false
    accept). Same shape as the table in docs/rag_config.md's Sprint 3
    threshold selection, just against the current corpus and eval set."""
    in_corpus = [r for r in runs if not r["is_off_topic"]]
    off_topic = [r for r in runs if r["is_off_topic"]]
    false_fallback_ids = [r["id"] for r in in_corpus if r["best_similarity"] < threshold]
    false_accept_ids = [r["id"] for r in off_topic if r["best_similarity"] >= threshold]
    return {
        "threshold": threshold,
        "in_corpus_false_fallbacks": len(false_fallback_ids),
        "false_fallback_ids": false_fallback_ids,
        "off_topic_correct_fallbacks": len(off_topic) - len(false_accept_ids),
        "off_topic_total": len(off_topic),
        "off_topic_false_accepts": len(false_accept_ids),
        "false_accept_ids": false_accept_ids,
    }


def sweep(runs: list, candidates: list = THRESHOLD_CANDIDATES) -> list:
    return [threshold_row(runs, t) for t in candidates]


def recommend_threshold(sweep_rows: list, current_threshold: float) -> dict:
    """Prefer the value closest to the current default that still separates
    in-corpus from off-topic cleanly (0 false fallbacks, 0 false accepts) --
    a change has to earn its keep, not just tie. If nothing in the grid is
    clean, keep the current default and flag it rather than guessing."""
    clean = [r for r in sweep_rows
             if r["in_corpus_false_fallbacks"] == 0 and r["off_topic_false_accepts"] == 0]
    if not clean:
        return {
            "recommended_threshold": current_threshold,
            "changed": False,
            "clean_candidate_found": False,
            "reason": (
                "No threshold in the grid separates in-corpus from off-topic "
                "questions cleanly on this corpus. Keeping the current "
                f"default ({current_threshold}) and flagging for manual "
                "review rather than picking a value that still gets some "
                "queries wrong."
            ),
        }
    best = min(clean, key=lambda r: abs(r["threshold"] - current_threshold))
    changed = best["threshold"] != current_threshold
    return {
        "recommended_threshold": best["threshold"],
        "changed": changed,
        "clean_candidate_found": True,
        "reason": (
            f"{best['threshold']} is the closest-to-default value that still "
            f"produces 0 false fallbacks and 0 false accepts on this corpus."
            if changed else
            f"Current default {current_threshold} still produces 0 false "
            "fallbacks and 0 false accepts on the wider corpus -- no change "
            "needed, reverting nothing."
        ),
    }


def load_sprint7_baseline() -> dict | None:
    if not SPRINT7_BASELINE.exists():
        return None
    return json.loads(SPRINT7_BASELINE.read_text(encoding="utf-8"))["summary"]


def write_markdown(corpus_size, metrics, sweep_rows, recommendation,
                    current_threshold, baseline, path: Path):
    lines = [
        "# Sprint 9 -- Retrieval Tuning Check (T9-10)",
        "",
        f"**Corpus size at run time: {corpus_size if corpus_size is not None else 'unknown'} chunks.**",
        "",
        "Ranking-quality re-run of the Sprint 7 benchmark: see "
        "`docs/retrieval_benchmark_sprint9.md` (produced by "
        "`BENCHMARK_SPRINT=9 python scripts/benchmark_retrieval.py`) for the "
        "full per-query table. This report covers the other half of T9-10: "
        "whether `SIMILARITY_THRESHOLD` still holds up on the wider corpus.",
        "",
        "## Before / After -- ranking quality",
        "",
        "| Metric | Sprint 7 (46 chunks) | Sprint 9 (this corpus) |",
        "|---|---:|---:|",
    ]
    if baseline:
        lines.append(f"| Precision@5 | {baseline.get('avg_precision_at_5')} | {metrics['avg_precision_at_5']} |")
        lines.append(f"| Recall@10 | {baseline.get('avg_recall_at_10')} | {metrics['avg_recall_at_10']} |")
        lines.append(f"| MRR | {baseline.get('mrr')} | {metrics['mrr']} |")
    else:
        lines.append("| (Sprint 7 baseline not found -- run from repo root) | -- | -- |")
    lines += [
        "",
        "## Threshold sweep",
        "",
        f"Current production default: `SIMILARITY_THRESHOLD = {current_threshold}`.",
        "",
        "| Threshold | In-corpus false fallbacks | Off-topic correct fallbacks | Off-topic false accepts |",
        "|---:|---:|---:|---:|",
    ]
    for r in sweep_rows:
        marker = " (current)" if r["threshold"] == current_threshold else ""
        lines.append(
            f"| {r['threshold']}{marker} | {r['in_corpus_false_fallbacks']} "
            f"({', '.join(r['false_fallback_ids']) or '--'}) | "
            f"{r['off_topic_correct_fallbacks']}/{r['off_topic_total']} | "
            f"{r['off_topic_false_accepts']} ({', '.join(r['false_accept_ids']) or '--'}) |"
        )
    lines += [
        "",
        "## Recommendation",
        "",
        f"**Recommended threshold: {recommendation['recommended_threshold']}** "
        f"({'change from' if recommendation['changed'] else 'no change from'} "
        f"current default {current_threshold}).",
        "",
        recommendation["reason"],
        "",
    ]
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
            "\nERROR: the ChromaDB collection is empty. Seed the corpus first "
            "-- see README.md / ingest_corpus.py. Not tuning against an "
            "empty collection."
        )
        sys.exit(1)
    print(f"Collection has {corpus_size} chunks.")

    print("\nRunning retrieval once per query...")
    runs = run_queries(eval_set, retriever)

    metrics = ranking_metrics(runs)
    sweep_rows = sweep(runs)
    recommendation = recommend_threshold(sweep_rows, SIMILARITY_THRESHOLD)
    baseline = load_sprint7_baseline()

    print("\n=== Ranking metrics (this corpus) ===")
    print(json.dumps(metrics, indent=2))
    print("\n=== Threshold sweep ===")
    print(json.dumps(sweep_rows, indent=2))
    print("\n=== Recommendation ===")
    print(json.dumps(recommendation, indent=2))

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "corpus_size": corpus_size,
        "current_threshold": SIMILARITY_THRESHOLD,
        "ranking_metrics": metrics,
        "threshold_sweep": sweep_rows,
        "recommendation": recommendation,
        "runs": runs,
    }, indent=2), encoding="utf-8")
    write_markdown(corpus_size, metrics, sweep_rows, recommendation,
                    SIMILARITY_THRESHOLD, baseline, OUT_MD)

    print(f"\nSaved: {OUT_JSON}")
    print(f"Saved: {OUT_MD}")


if __name__ == "__main__":
    main()