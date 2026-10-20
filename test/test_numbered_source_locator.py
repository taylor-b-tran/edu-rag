"""Exact numbered exercise references retain provenance and course isolation."""
import json
from unittest.mock import Mock
import pytest
from src.document_processor.source_context import pdf_source_context, query_locator
from src.document_processor import rag_pipeline as rp

INSTRUCTION = "Part I: For each of these True-or-False statements, determine whether it is true or false."


@pytest.mark.parametrize("query,expected", [
    ("What does statement 16 of Part I ask?", ("part:1", "16")),
    ("quote question #3 in Section IV", ("section:4", "3")),
    ("item 09 of part 2", ("part:2", "9")),
    ("statement 16", None),
    ("statement 16 of Part I and statement 17 of Part II", None),
])
def test_query_locators(query, expected):
    assert query_locator(query) == expected


def test_continuation_items_are_complete_and_end_at_section_boundary():
    _, active = pdf_source_context(INSTRUCTION + "\n1. First proposition.", 1)
    meta, active = pdf_source_context("15. Previous.\n16. A proposition with\nwrapped text.\n17. Incomplete", 2, active)
    assert meta["source_section"] == "part:1"
    assert json.loads(meta["source_items"]) == {"15": "Previous.", "16": "A proposition with wrapped text."}
    ended, _ = pdf_source_context("Part II: Reading\n16. Not an exercise proposition.", 3, active)
    assert "source_items" not in ended


def retriever_with(*records):
    ret = object.__new__(rp.VectorRetriever)
    ret._collection = Mock()
    ret._collection.get.return_value = {"ids": [str(i) for i in range(len(records))], "metadatas": records}
    return ret


def meta(source="Workshop_02.pdf", **extra):
    return dict(source_file=source, page_number=2, source_kind="exercise_prompt",
                source_items=json.dumps({"16": "A proposition to evaluate."}), **extra)


def test_lookup_deduplicates_page_chunks_and_never_drops_course_filter():
    ret = retriever_with(meta(), meta())
    hits = ret._locate_item("statement 16 of Part I", "COURSE123")
    assert len(hits) == 1 and hits[0].locator_match and hits[0].similarity == 0
    where = ret._collection.get.call_args.kwargs["where"]
    assert where == {"$and": [{"course_id": {"$eq": "COURSE123"}}, {"source_section": {"$eq": "part:1"}}]}


def test_document_hint_selects_correct_workshop_and_scope():
    ret = retriever_with(meta("Workshop_01.pdf"), meta(), meta("Workshop_02-other.pdf", source_scope="OTHER999"))
    assert [c.source_file for c in ret._locate_item("Workshop 2 statement 16 of Part I", "COURSE123")] == ["Workshop_02.pdf"]
    assert ret._locate_item("Workshop 99 statement 16 of Part I", "COURSE123") == []


def test_ambiguity_is_not_hidden_by_top_k_or_sent_to_model():
    ret = Mock()
    ret.search.return_value = retriever_with(meta(), meta("Workshop_03.pdf"))._locate_item("statement 16 of Part I", "COURSE123")
    gen = rp.LLMResponseGeneration(ret)
    gen._call_ollama = Mock(side_effect=AssertionError("Must clarify before generation"))
    result = gen.generate("statement 16 of Part I", "COURSE123", top_k=1)
    assert "Which document" in result.answer and len(result.source_refs) == 2
    assert result.confidence_score == 0


def test_exact_match_survives_similarity_threshold_without_inflated_score():
    ret = Mock()
    ret.search.return_value = retriever_with(meta())._locate_item("statement 16 of Part I", "COURSE123")
    gen = rp.LLMResponseGeneration(ret)
    gen._call_ollama = Mock(return_value=("The exercise asks you to evaluate this proposition [S1].", True))
    result = gen.generate("statement 16 of Part I", "COURSE123", similarity_threshold=.99)
    assert len(result.source_refs) == 1 and not result.is_fallback
    assert result.confidence == "Low" and result.confidence_score == 0


def test_missing_exact_locator_does_not_answer_a_different_number():
    ret = Mock()
    ret.search.return_value = [rp.RetrievedChunk("x", "Statement 15: Other.", "Workshop.pdf", 2, "", "", .1)]
    gen = rp.LLMResponseGeneration(ret)
    gen._call_ollama = Mock(side_effect=AssertionError("Do not guess"))
    result = gen.generate("statement 999 of Part I", "COURSE123")
    assert "could not locate" in result.answer and result.source_refs == []


@pytest.mark.parametrize("query", [
    "Quote statement 16 of Part I in Workshop 02 as an exercise question, not as a fact.",
    "In Workshop 2, what does statement 16 of Part I ask us to evaluate?",
])
def test_quotation_keeps_provenance_without_a_generated_truth_claim(query):
    ret = Mock()
    ret.search.return_value = retriever_with(meta())._locate_item(query, "COURSE123")
    gen = rp.LLMResponseGeneration(ret)
    gen._call_ollama = Mock(side_effect=AssertionError("Quotation requires no model judgement"))
    result = gen.generate(query, "COURSE123")
    assert result.answer.startswith("Statement 16: A proposition to evaluate. [S1]")
    assert len(result.source_refs) == 1 and not result.is_fallback and result.confidence_score == 0


def test_truth_question_still_requires_grounded_generation():
    ret = Mock()
    ret.search.return_value = retriever_with(meta())._locate_item("statement 16 of Part I", "COURSE123")
    gen = rp.LLMResponseGeneration(ret)
    gen._call_ollama = Mock(return_value=(rp.REFUSAL_SENTENCE, True))
    result = gen.generate("Is statement 16 of Part I true?", "COURSE123")
    gen._call_ollama.assert_called_once()
    assert result.is_fallback and result.source_refs == []


def test_bare_section_heading_does_not_inherit_previous_item_numbers():
    _, active = pdf_source_context(INSTRUCTION + "\n1. First proposition.", 1)
    meta, active = pdf_source_context("Part II\n16. A new reading task.", 2, active)
    assert active is None and "source_items" not in meta


def test_indexing_preserves_locator_metadata(monkeypatch, tmp_path):
    from src.api.routes.documents import _bg_index_document
    from src.document_processor import chunker, ingest_corpus
    monkeypatch.setattr(chunker, "extract_and_chunk", lambda path: [
        {"text": "Proposition.", "metadata": {"source_section": "part:1", "source_items": '{"16":"Proposition."}'}}])
    collection = Mock()
    monkeypatch.setattr(ingest_corpus, "get_chroma_client", Mock())
    monkeypatch.setattr(ingest_corpus, "get_or_create_collection", lambda _: collection)
    model = Mock()
    model.encode.return_value = [[0.] * 384]
    monkeypatch.setattr(ingest_corpus, "_load_embedder", lambda: (model, "model", 384))
    _bg_index_document(tmp_path/"worksheet.pdf", "COURSE123", "doc", "job", Mock())
    meta = collection.upsert.call_args.kwargs["metadatas"][0]
    assert meta["source_section"] == "part:1" and meta["source_items"] == '{"16":"Proposition."}'
