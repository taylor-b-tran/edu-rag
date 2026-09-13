import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.tune_retrieval import (
    ranking_metrics, threshold_row, sweep, recommend_threshold,
)


def _run(id_, retrieved, relevant, best_similarity):
    return {
        "id": id_,
        "is_off_topic": len(relevant) == 0,
        "relevant_chunk_ids": relevant,
        "retrieved_ids": retrieved,
        "best_similarity": best_similarity,
    }


def test_ranking_metrics_ignores_off_topic_queries():
    runs = [
        _run("Q1", ["a", "b"], ["a"], 0.5),
        _run("Q2", ["x", "y"], [], 0.1),  # off-topic: no ground truth
    ]
    metrics = ranking_metrics(runs)
    assert metrics["avg_precision_at_5"] == 0.5  # only Q1 counted, 1/2 top-2... precision@5 over 2 items
    assert metrics["mrr"] == 1.0


def test_ranking_metrics_empty_in_corpus_is_none():
    runs = [_run("Q1", ["x"], [], 0.1)]
    metrics = ranking_metrics(runs)
    assert metrics["avg_precision_at_5"] is None
    assert metrics["avg_recall_at_10"] is None
    assert metrics["mrr"] is None


def test_threshold_row_counts_false_fallback():
    # in-corpus query whose best similarity is below the candidate threshold
    runs = [_run("Q1", ["a"], ["a"], 0.30)]
    row = threshold_row(runs, threshold=0.35)
    assert row["in_corpus_false_fallbacks"] == 1
    assert row["false_fallback_ids"] == ["Q1"]


def test_threshold_row_counts_correct_fallback_for_off_topic():
    runs = [_run("Q1", ["x"], [], 0.10)]  # off-topic, correctly below threshold
    row = threshold_row(runs, threshold=0.35)
    assert row["off_topic_correct_fallbacks"] == 1
    assert row["off_topic_false_accepts"] == 0


def test_threshold_row_counts_false_accept_for_off_topic():
    runs = [_run("Q1", ["x"], [], 0.90)]  # off-topic, wrongly above threshold
    row = threshold_row(runs, threshold=0.35)
    assert row["off_topic_correct_fallbacks"] == 0
    assert row["off_topic_false_accepts"] == 1
    assert row["false_accept_ids"] == ["Q1"]


def test_sweep_runs_every_candidate():
    runs = [_run("Q1", ["a"], ["a"], 0.40)]
    rows = sweep(runs, candidates=[0.2, 0.5])
    assert [r["threshold"] for r in rows] == [0.2, 0.5]


def test_recommend_keeps_current_when_it_is_clean():
    # current=0.35 is clean; nothing should change
    sweep_rows = [
        {"threshold": 0.20, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 1},
        {"threshold": 0.35, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 0},
        {"threshold": 0.50, "in_corpus_false_fallbacks": 1, "off_topic_false_accepts": 0},
    ]
    rec = recommend_threshold(sweep_rows, current_threshold=0.35)
    assert rec["recommended_threshold"] == 0.35
    assert rec["changed"] is False


def test_recommend_picks_closest_clean_value_when_current_is_dirty():
    # current=0.35 has a false accept; 0.40 is the nearest clean candidate
    sweep_rows = [
        {"threshold": 0.20, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 1},
        {"threshold": 0.35, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 1},
        {"threshold": 0.40, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 0},
        {"threshold": 0.50, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 0},
    ]
    rec = recommend_threshold(sweep_rows, current_threshold=0.35)
    assert rec["recommended_threshold"] == 0.40
    assert rec["changed"] is True


def test_recommend_falls_back_to_current_when_nothing_is_clean():
    sweep_rows = [
        {"threshold": 0.20, "in_corpus_false_fallbacks": 0, "off_topic_false_accepts": 1},
        {"threshold": 0.50, "in_corpus_false_fallbacks": 1, "off_topic_false_accepts": 0},
    ]
    rec = recommend_threshold(sweep_rows, current_threshold=0.35)
    assert rec["recommended_threshold"] == 0.35
    assert rec["changed"] is False
    assert rec["clean_candidate_found"] is False