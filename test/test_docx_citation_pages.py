import sys
from pathlib import Path
from unittest.mock import Mock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.document_processor.rag_pipeline import (
    VectorRetriever,
    RetrievedChunk,
    LLMResponseGeneration,
)
from main import _citation_page_label


def test_docx_chunks_indexed_without_invented_page(monkeypatch, tmp_path):
    from src.api.routes.documents import _bg_index_document
    from src.document_processor import chunker, ingest_corpus

    chunk_data = [
        {"text": "docx chunk", "metadata": {"source": "n.docx", "format": "docx", "chunk_index": 0}},
        {"text": "pdf chunk", "metadata": {"source": "p.pdf", "format": "pdf", "page_number": 7}},
        {"text": "pptx chunk", "metadata": {"source": "s.pptx", "format": "pptx", "slide_number": 3}},
    ]
    monkeypatch.setattr(chunker, "extract_and_chunk", lambda path: chunk_data)

    client = Mock()
    collection = Mock()
    monkeypatch.setattr(ingest_corpus, "get_chroma_client", lambda: client)
    monkeypatch.setattr(ingest_corpus, "get_or_create_collection", lambda c: collection)

    model = Mock()
    model.encode.return_value = [[0.0] * 384, [0.0] * 384, [0.0] * 384]
    monkeypatch.setattr(ingest_corpus, "_load_embedder", lambda: (model, "m", 384))

    state = Mock()
    file_path = tmp_path / "n-ab12cd34.docx"
    file_path.write_text("dummy")

    _bg_index_document(file_path, "CSIT321", "doc", "job", state)

    assert collection.upsert.called
    metas = collection.upsert.call_args.kwargs["metadatas"]
    assert metas[0]["page_number"] == 0
    assert metas[1]["page_number"] == 7
    assert metas[2]["page_number"] == 3


def test_retriever_drops_page_for_docx_including_legacy_chunks():
    r = object.__new__(VectorRetriever)
    r._model = Mock()
    r._model.encode.return_value = [0.0] * 384
    r._collection = Mock()
    r._collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    r._collection.query.return_value = {
        "ids": [["c1", "c2"]],
        "documents": [["doc1", "doc2"]],
        "distances": [[0.1, 0.2]],
        "metadatas": [[
            {"source_file": "n-ab12cd34.docx", "page_number": 1, "topic": "t1", "week": "w1"},
            {"source_file": "w1.pdf", "page_number": 4, "topic": "t2", "week": "w2"},
        ]],
    }
    hits = r.search("dummy question", course_id="CSIT321", top_k=2)
    assert len(hits) == 2
    assert [h.page_number for h in hits] == [0, 4]


def test_pageless_ref_reports_none():
    chunks = [
        RetrievedChunk(
            chunk_id="c1", text="some docx text",
            source_file="n-ab12cd34.docx", page_number=0,
            topic="Notes", week="1", distance=0.2,
        ),
        RetrievedChunk(
            chunk_id="c2", text="some pdf text",
            source_file="w1.pdf", page_number=4,
            topic="Lecture", week="1", distance=0.3,
        ),
    ]
    refs, positions = LLMResponseGeneration._refs_with_positions(chunks)
    assert len(refs) == 2
    assert [r["page"] for r in refs] == [None, 4]


class _StubRetriever:
    def search(self, *a, **kw):
        return []


def _generator(strategy):
    return LLMResponseGeneration(retriever=_StubRetriever(), strategy=strategy)


@pytest.mark.parametrize("strategy", ["baseline", "evidence_cited", "few_shot_cited"])
def test_prompt_has_no_p0_marker(strategy):
    chunks = [
        RetrievedChunk(
            chunk_id="c1", text="docx content",
            source_file="n.docx", page_number=0,
            topic="Notes", week="1", distance=0.2,
        ),
    ]
    gen = _generator(strategy)
    prompt = gen._build_prompt("What is in notes?", chunks)
    assert "n.docx" in prompt
    assert "p.0" not in prompt


def test_citation_page_label():
    assert _citation_page_label({"filename": "notes.docx", "page": 1}) == ""
    assert _citation_page_label({"source_file": "n-ab12cd34.docx", "page": 0}) == ""
    assert _citation_page_label({"filename": "w1.pdf", "page": 4}) == "p.4"
    assert _citation_page_label({"filename": "deck.pptx", "page_number": 3}) == "p.3"
    assert _citation_page_label({"filename": "w1.pdf"}) == ""
