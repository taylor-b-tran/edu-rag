import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark_retrieval import precision_at_k, recall_at_k, reciprocal_rank


def test_precision_at_k_all_relevant():
    retrieved = ["a", "b", "c", "d", "e"]
    relevant = {"a", "b", "c", "d", "e"}
    assert precision_at_k(retrieved, relevant, 5) == 1.0


def test_precision_at_k_partial_match():
    retrieved = ["a", "x", "b", "y", "z"]
    relevant = {"a", "b"}
    # 2 of the top 5 are relevant
    assert precision_at_k(retrieved, relevant, 5) == 0.4


def test_precision_at_k_no_match():
    retrieved = ["x", "y", "z"]
    relevant = {"a", "b"}
    assert precision_at_k(retrieved, relevant, 3) == 0.0


def test_recall_at_k_finds_all_relevant():
    retrieved = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    relevant = {"a", "j"}
    assert recall_at_k(retrieved, relevant, 10) == 1.0


def test_recall_at_k_misses_some():
    retrieved = ["a", "x", "y"]
    relevant = {"a", "b"}  # "b" never retrieved
    assert recall_at_k(retrieved, relevant, 3) == 0.5


def test_recall_at_k_undefined_for_no_ground_truth():
    # off-topic queries have no relevant chunks -- recall is undefined, not 0
    assert recall_at_k(["a", "b"], set(), 10) is None


def test_reciprocal_rank_first_position():
    assert reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0


def test_reciprocal_rank_third_position():
    assert reciprocal_rank(["x", "y", "a"], {"a"}) == round(1 / 3, 3)


def test_reciprocal_rank_not_found():
    assert reciprocal_rank(["x", "y", "z"], {"a"}) == 0.0


def test_reciprocal_rank_undefined_for_no_ground_truth():
    assert reciprocal_rank(["a", "b"], set()) is None
