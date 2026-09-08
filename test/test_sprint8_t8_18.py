"""
T8-18 -- follow-up conversation support:

1. Pass the session's last 3 turns into generate().
2. Filter citations.
3. Resolve pronouns/references before retrieval via a dedicated Ollama
   rewrite call.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.rag_pipeline import (
    LLMResponseGeneration,
    RetrievedChunk,
    _extract_cited_source_indices,
    _strip_invalid_citation_markers,
)


class _StubRetriever:
    """Records every query it was searched with, and returns a fixed
    (possibly empty) chunk list regardless of the query."""
    def __init__(self, chunks=None):
        self.calls = []
        self._chunks = chunks if chunks is not None else []

    def search(self, query, *a, **kw):
        self.calls.append(query)
        return self._chunks


@pytest.fixture
def two_chunks():
    return [
        RetrievedChunk(
            chunk_id="c1", text="A neuron sums weighted inputs and applies an activation function.",
            source_file="Week3_NeuralNetworks.pdf", page_number=1,
            topic="Neural Networks", week="3", distance=0.1,
        ),
        RetrievedChunk(
            chunk_id="c2", text="Backpropagation computes gradients layer by layer via the chain rule.",
            source_file="Week3_NeuralNetworks.pdf", page_number=4,
            topic="Neural Networks", week="3", distance=0.2,
        ),
    ]


SAMPLE_HISTORY_3_TURNS = [
    {"question": "What is a neural network?", "answer": "A model of connected neurons that learn from data [S1]."},
    {"question": "What is a neuron made of?", "answer": "Weighted inputs and an activation function [S2]."},
    {"question": "How is it trained?", "answer": "Via backpropagation and gradient descent [S3]."},
]

# Requirement 1 -- last 3 turns reach the prompt
def test_last_3_turns_reach_the_prompt(two_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompt = gen._build_prompt("explain it deeply", two_chunks, history=SAMPLE_HISTORY_3_TURNS)
    for turn in SAMPLE_HISTORY_3_TURNS:
        assert turn["question"] in prompt


def test_only_last_3_turns_kept_when_more_exist(two_chunks):
    long_history = [
        {"question": f"Question {i}", "answer": f"Answer {i}"} for i in range(1, 8)
    ]
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompt = gen._build_prompt("follow up", two_chunks, history=long_history)
    assert "Question 7" in prompt
    assert "Question 6" in prompt
    assert "Question 5" in prompt
    assert "Question 4" not in prompt
    assert "Question 1" not in prompt


def test_no_history_prompt_has_no_history_section(two_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    prompt = gen._build_prompt("What is RAG?", two_chunks, history=None)
    assert "[HISTORY]" not in prompt

# Requirement 2 -- strip citations not in the CURRENT turn (merge-blocking)
def test_exact_repro_zero_chunks_still_cited(monkeypatch):
    """Current turn retrieves 0 chunks, model still emits [S2]/[S3]copied from
    a previous turn. Must not reach the student as text or as source_refs."""
    gen = LLMResponseGeneration(retriever=_StubRetriever(chunks=[]))
    monkeypatch.setattr(
        gen, "_call_ollama",
        lambda prompt, chunks=None, **kwargs: (
            "Backprop updates weights using gradients [S2], as covered before [S3].\n\nSources: S2, S3",
            True,
        ),
    )
    result = gen.generate("explain it deeply", history=SAMPLE_HISTORY_3_TURNS)

    assert "[S2]" not in result.answer
    assert "[S3]" not in result.answer
    assert "Sources: S2" not in result.answer
    assert result.source_refs == []
    # The sentence itself must survive -- only the marker is removed.
    assert "Backprop updates weights using gradients" in result.answer


def test_valid_citations_survive_when_chunks_exist(two_chunks, monkeypatch):
    gen = LLMResponseGeneration(retriever=_StubRetriever(chunks=two_chunks))
    monkeypatch.setattr(
        gen, "_call_ollama",
        lambda prompt, chunks=None, **kwargs: (
            "A neuron sums weighted inputs [S1]. Training uses backprop [S2].\n\nSources: S1, S2",
            True,
        ),
    )
    result = gen.generate("What is a neuron?")
    assert "[S1]" in result.answer
    assert "[S2]" in result.answer
    files = {r["source_file"] for r in result.source_refs}
    assert files == {"Week3_NeuralNetworks.pdf"}


def test_mixed_valid_and_stale_citations(two_chunks, monkeypatch):
    """2 real current-turn chunks, model also hallucinates a stale S5."""
    gen = LLMResponseGeneration(retriever=_StubRetriever(chunks=two_chunks))
    monkeypatch.setattr(
        gen, "_call_ollama",
        lambda prompt, chunks=None, **kwargs: (
            "Neurons sum inputs [S1]. Backprop trains the network [S2]. Covered in week 3 [S5].\n\nSources: S1, S2, S5",
            True,
        ),
    )
    result = gen.generate("How do neurons work?")
    assert "[S1]" in result.answer
    assert "[S2]" in result.answer
    assert "[S5]" not in result.answer
    assert "S5" not in result.answer.split("Sources:")[-1]


def test_strip_invalid_citation_markers_keeps_sentence_text():
    text = "This is important [S4]."
    cleaned = _strip_invalid_citation_markers(text, num_chunks=0)
    assert cleaned == "This is important."


def test_strip_invalid_citation_markers_no_markers_unchanged():
    text = "No citations in this sentence at all."
    assert _strip_invalid_citation_markers(text, num_chunks=3) == text


def test_extract_cited_indices_ignores_stale_out_of_range():
    # Same underlying rule that source_refs relies on -- 0 current chunks
    # means nothing can be a valid citation, regardless of what's in the text.
    answer = "Copied from before [S2] [S3]."
    assert _extract_cited_source_indices(answer, num_chunks=0) == set()

# Requirement 3 -- pronoun/reference resolution before retrieval
def test_no_history_retrieval_uses_literal_question(two_chunks, monkeypatch):
    retriever = _StubRetriever(chunks=two_chunks)
    gen = LLMResponseGeneration(retriever=retriever)
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None, **kwargs: ("answer", True))
    gen.generate("What is a neuron?")
    assert retriever.calls == ["What is a neuron?"]


def test_follow_up_is_rewritten_before_retrieval(two_chunks, monkeypatch):
    """Retrieval must search for something resolved, not the bare word 'it'."""
    retriever = _StubRetriever(chunks=two_chunks)
    gen = LLMResponseGeneration(retriever=retriever)
    monkeypatch.setattr(
        gen, "_call_ollama_lightweight",
        lambda prompt, **kw: ("Explain how neural networks work in depth", True),
    )
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None, **kwargs: ("answer", True))

    history = [{"question": "what is neuron network", "answer": "A model of connected neurons."}]
    gen.generate("explain it deeply", history=history)

    assert retriever.calls == ["Explain how neural networks work in depth"]
    assert "it" not in retriever.calls[0].lower().split()


def test_rewrite_uses_a_real_llm_call_not_a_shortcut(two_chunks, monkeypatch):
    """Confirms requirement 3 picked 'option 2': an actual model call for
    the rewrite, not a regex/keyword substitution."""
    retriever = _StubRetriever(chunks=two_chunks)
    gen = LLMResponseGeneration(retriever=retriever)
    calls = []
    monkeypatch.setattr(
        gen, "_call_ollama_lightweight",
        lambda prompt, **kw: (calls.append(prompt), ("resolved question", True))[1],
    )
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None, **kwargs: ("answer", True))
    gen.generate("explain it deeply", history=SAMPLE_HISTORY_3_TURNS)
    assert len(calls) == 1
    assert "REWRITTEN QUESTION" in calls[0] or "rewrite" in calls[0].lower()


def test_rewrite_failure_falls_back_to_original_question(two_chunks, monkeypatch):
    retriever = _StubRetriever(chunks=two_chunks)
    gen = LLMResponseGeneration(retriever=retriever)
    monkeypatch.setattr(gen, "_call_ollama_lightweight", lambda prompt, **kw: ("", False))
    monkeypatch.setattr(gen, "_call_ollama", lambda prompt, chunks=None, **kwargs: ("answer", True))
    gen.generate("explain it deeply", history=SAMPLE_HISTORY_3_TURNS)
    assert retriever.calls == ["explain it deeply"]


def test_original_question_still_shown_to_model_for_the_answer(two_chunks, monkeypatch):
    """Only retrieval uses the rewritten form -- the model must still see
    the student's literal question so the answer addresses what they
    actually asked."""
    retriever = _StubRetriever(chunks=two_chunks)
    gen = LLMResponseGeneration(retriever=retriever)
    monkeypatch.setattr(
        gen, "_call_ollama_lightweight",
        lambda prompt, **kw: ("Explain neural networks in depth", True),
    )
    captured = []
    monkeypatch.setattr(
        gen, "_call_ollama",
        lambda prompt, chunks=None, **kwargs: (captured.append(prompt), ("answer", True))[1],
    )
    gen.generate("explain it deeply", history=SAMPLE_HISTORY_3_TURNS)
    assert "explain it deeply" in captured[0]
