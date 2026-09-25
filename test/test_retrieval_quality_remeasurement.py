"""T17: retrieval figures must be reported alongside the corpus-imbalance
caveat, and a question whose top hits stray into unrelated topics must be
surfaced automatically rather than relying on someone noticing by eye.
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.benchmark_retrieval import (
    corpus_document_distribution, run_benchmark, summarise,
)


class _FakeCollection:
    def __init__(self, metadatas):
        self._metadatas = metadatas

    def get(self, include=None):
        return {"metadatas": self._metadatas}


class _FailingCollection:
    def get(self, include=None):
        raise RuntimeError("collection unavailable")


def test_reports_the_share_of_the_dominant_document():
    metas = (
        [{"source_file": "book_embNLP_draft.pdf"}] * 60
        + [{"source_file": "Week1.pdf"}] * 20
        + [{"source_file": "Week3.pdf"}] * 20
    )
    dist = corpus_document_distribution(_FakeCollection(metas))
    assert dist["available"] is True
    assert dist["total_chunks"] == 100
    assert dist["top_document"] == "book_embNLP_draft.pdf"
    assert dist["top_document_share"] == 0.6


def test_an_even_corpus_is_not_flagged_as_imbalanced():
    metas = [{"source_file": f"Week{i}.pdf"} for i in range(1, 11)]
    dist = corpus_document_distribution(_FakeCollection(metas))
    summary = summarise([], corpus_size=10, distribution=dist)
    assert summary["corpus_imbalance_flagged"] is False


def test_a_dominant_document_is_flagged_as_imbalanced():
    metas = [{"source_file": "big.pdf"}] * 55 + [{"source_file": "small.pdf"}] * 45
    dist = corpus_document_distribution(_FakeCollection(metas))
    summary = summarise([], corpus_size=100, distribution=dist)
    assert summary["corpus_imbalance_flagged"] is True


def test_missing_source_file_falls_back_to_unknown_rather_than_erroring():
    dist = corpus_document_distribution(_FakeCollection([{}, {}]))
    assert dist["available"] is True
    assert dist["top_document"] == "Unknown"


def test_an_unavailable_collection_is_reported_not_raised():
    assert corpus_document_distribution(_FailingCollection()) == {"available": False}


def test_an_empty_collection_is_reported_not_divided_by_zero():
    assert corpus_document_distribution(_FakeCollection([])) == {"available": False}


# Topic dispersion: the "citations drawn from unrelated topics" case

class _FakeChunk:
    def __init__(self, chunk_id, topic, similarity=0.8):
        self.chunk_id = chunk_id
        self.topic = topic
        self.similarity = similarity


class _FakeRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    def search(self, question, course_id=None, top_k=None):
        return self._chunks[:top_k] if top_k else self._chunks


def test_a_question_whose_top_hits_stay_on_topic_is_not_flagged():
    eval_set = [{"id": "Q1", "question": "q", "topic": "Sorting", "relevant_chunk_ids": ["a"]}]
    chunks = [_FakeChunk("a", "Sorting"), _FakeChunk("b", "Sorting")]
    results = run_benchmark(eval_set, _FakeRetriever(chunks))
    assert results[0]["topic_dispersion_flag"] is False
    assert results[0]["unrelated_topics_hit"] == []


def test_a_question_that_pulls_in_an_unrelated_topic_is_flagged():
    eval_set = [{"id": "Q1", "question": "How does binary search work?",
                 "topic": "Algorithms", "relevant_chunk_ids": ["a"]}]
    chunks = [_FakeChunk("a", "Algorithms"), _FakeChunk("x", "Vector Embeddings"),
              _FakeChunk("y", "Flask API")]
    results = run_benchmark(eval_set, _FakeRetriever(chunks))
    assert results[0]["topic_dispersion_flag"] is True
    assert results[0]["unrelated_topics_hit"] == ["Flask API", "Vector Embeddings"]


def test_off_topic_control_questions_are_never_flagged_for_dispersion():
    """An off-topic control question has no relevant chunks by design -- it
    isn't a real weak result, so it shouldn't clutter the dispersion list."""
    eval_set = [{"id": "R21", "question": "weather forecast", "topic": "off_topic",
                 "relevant_chunk_ids": []}]
    chunks = [_FakeChunk("z", "Ollama & LLM Generation")]
    results = run_benchmark(eval_set, _FakeRetriever(chunks))
    assert results[0]["topic_dispersion_flag"] is False
