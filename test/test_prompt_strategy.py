import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.rag_pipeline import LLMResponseGeneration, RetrievedChunk

@pytest.fixture
def sample_chunks():
    return [
        RetrievedChunk(
            chunk_id="c1", text="RAG retrieves relevant chunks before generation.",
            source_file="Week1_RAG_Introduction.pdf", page_number=2,
            topic="RAG Fundamentals", week="1", distance=0.2,
        ),
        RetrievedChunk(
            chunk_id="c2", text="ChromaDB stores embeddings with metadata filtering.",
            source_file="Week3_ChromaDB_VectorStore.pdf", page_number=5,
            topic="Vector database", week="3", distance=0.3,
        ),
    ]

class _StubRetriever:
    """Avoids needing a real ChromaDB collection / embedder for this unit test."""
    def search(self, *a, **kw):
        return []

def _generator(strategy):
    return LLMResponseGeneration(retriever=_StubRetriever(), strategy=strategy)

def test_baseline_prompt_has_no_citation_ids(sample_chunks):
    gen = _generator("baseline")
    prompt = gen._build_prompt("What is RAG?", sample_chunks)
    assert "[S1]" not in prompt
    assert "Week1_RAG_Introduction.pdf" in prompt

def test_evidence_cited_prompt_forces_citation_ids(sample_chunks):
    gen = _generator("evidence_cited")
    prompt = gen._build_prompt("What is RAG?", sample_chunks)
    assert "[S1]" in prompt
    assert "[S2]" in prompt
    assert "Sources:" in prompt
    assert "Cite every main claim" in prompt

def test_default_strategy_is_evidence_cited(sample_chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever())
    assert gen.strategy == "evidence_cited"
    prompt = gen._build_prompt("What is RAG?", sample_chunks)
    assert "[S1]" in prompt

def test_no_context_fallback_label_present_both_strategies():
    for strat in ("baseline", "evidence_cited", "few_shot_cited"):
        gen = _generator(strat)
        prompt = gen._build_prompt("Random question", [])
        assert "NO COURSE MATERIAL FOUND" in prompt

def test_few_shot_cited_includes_worked_example_and_citations(sample_chunks):
    gen = _generator("few_shot_cited")
    prompt = gen._build_prompt("What is RAG?", sample_chunks)
    assert "Example of the required format" in prompt
    assert "[S1]" in prompt
    assert "Sources:" in prompt
    # the worked example must still come before the actual student question
    assert prompt.index("Example of the required format") < prompt.index("[STUDENT QUESTION]")

def test_generation_params_are_configurable(monkeypatch):
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.5")
    monkeypatch.setenv("OLLAMA_TOP_P", "0.8")
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "300")
    # reload the module so the env vars are re-read at import time
    import importlib
    from src.document_processor import rag_pipeline
    importlib.reload(rag_pipeline)
    assert rag_pipeline.OLLAMA_TEMPERATURE == 0.5
    assert rag_pipeline.OLLAMA_TOP_P == 0.8
    assert rag_pipeline.OLLAMA_NUM_PREDICT == 300
    importlib.reload(rag_pipeline)  # restore defaults for other tests
