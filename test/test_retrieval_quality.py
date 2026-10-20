from unittest.mock import Mock
import fitz
import pytest
from src.document_processor.chunker import extract_and_chunk
from src.document_processor.retrieval_ranking import rerank, expand_assessment_reference, lexical_candidates
from src.document_processor import rag_pipeline as rp


def chunk(text="Generic overview.", distance=.6, **kwargs):
    return rp.RetrievedChunk("id", text, "material.pdf", 1, "", "", distance, **kwargs)


def test_content_specific_terms_beat_a_generic_assessment_summary():
    generic = chunk("Assignment 7 is worth 15%. See the subject outline.", .57)
    detail = chunk("Assignment 7: Analyse the purpose of the nonces NA and NB (2 marks).", .63)
    query = "In Assignment 7, what is the purpose of nonces NA and NB and how many marks?"
    assert rerank(query, [generic]*7+[detail], .35)[0] is detail
    assert detail.similarity == pytest.approx(.37)


def test_lexical_match_cannot_promote_a_semantically_unrelated_passage():
    low = chunk("nonce nonce NA NB assignment marks", .95)
    good = chunk("Purpose of authentication challenges.", .5)
    assert rerank("nonce NA NB assignment marks", [low,good], .35)[0] is good


def test_ranking_without_lexical_overlap_keeps_semantic_order():
    high,low = chunk("alpha", .1),chunk("beta", .4)
    assert rerank("unseen", [low,high], .35)==[high,low]
    assert rerank("query", [], .35)==[]


def image_pdf(path, text, rect):
    with fitz.open() as pdf:
        page=pdf.new_page()
        page.insert_textbox(fitz.Rect(30,30,550,200), text, fontsize=11)
        pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,400,400),False)
        pix.clear_with(255)
        page.insert_image(rect,stream=pix.tobytes("png"))
        pdf.save(path)


def test_large_image_and_title_are_marked_as_sparse_not_factual_body(tmp_path):
    path=tmp_path/"slides.pdf"
    image_pdf(path,"Creating the Work Breakdown Structure (2 of 9)",fitz.Rect(30,220,550,780))
    rows=extract_and_chunk(path)
    assert rows and all(x["metadata"]["text_quality"]=="image_text_sparse" for x in rows)


def test_logo_does_not_disqualify_concise_text(tmp_path):
    path=tmp_path/"logo.pdf"
    image_pdf(path,"A stack removes the last inserted element first.",fitz.Rect(500,700,540,740))
    assert all("text_quality" not in x["metadata"] for x in extract_and_chunk(path))


def test_substantial_text_is_retained_even_with_a_large_illustration(tmp_path):
    path=tmp_path/"lecture.pdf"
    image_pdf(path,"A stack removes the last inserted element first. "*5,fitz.Rect(30,220,550,780))
    assert all("text_quality" not in x["metadata"] for x in extract_and_chunk(path))


def test_sparse_text_cannot_raise_confidence_or_enter_generation():
    sparse=chunk("Creating the Work Breakdown Structure",.05,text_quality="image_text_sparse")
    ret=Mock(); ret.search.return_value=[sparse]
    gen=rp.LLMResponseGeneration(ret)
    gen._call_ollama=Mock(side_effect=AssertionError("Do not invent image contents"))
    result=gen.generate("What is a work breakdown structure?")
    assert result.confidence=="Low" and result.confidence_score==0
    assert result.is_fallback and not result.source_refs
    assert "images" in result.answer and "text-accessible copy" in result.answer
    assert gen._confidence([sparse])==("Low",0.0)


def test_sparse_text_is_removed_when_a_readable_source_exists():
    sparse=chunk("Heading.",.01,text_quality="image_text_sparse")
    readable=chunk("A WBS divides project deliverables into work packages.",.5)
    ret=Mock(); ret.search.return_value=[sparse,readable]
    gen=rp.LLMResponseGeneration(ret)
    gen._call_ollama=Mock(return_value=("Work packages organise the deliverables [S1].",True))
    result=gen.generate("What is a WBS?")
    assert gen._call_ollama.call_args.kwargs["chunks"]==[readable]
    assert result.confidence=="Medium" and result.confidence_score==.5


def test_cited_absence_claim_is_not_treated_as_verified():
    ret=Mock(); ret.search.return_value=[chunk(distance=.1)]
    gen=rp.LLMResponseGeneration(ret)
    gen._call_ollama=Mock(return_value=("This detail "+rp.REFUSAL_SENTENCE+" [S1].",True))
    result=gen.generate("What does the assignment ask?")
    assert result.is_fallback and result.confidence_score==0 and result.source_refs==[]


def test_reranking_preserves_authorised_course_and_subject_filter():
    ret=object.__new__(rp.VectorRetriever)
    ret._model=Mock(); ret._model.encode.return_value=[0.] * 384
    ret._collection=Mock()
    ret._collection.get.return_value={"ids":[],"documents":[],"metadatas":[]}
    ret._collection.query.return_value={
        "ids":[["wrong","right"]],"documents":[["NA NB nonces"]*2],"distances":[[.1,.5]],
        "metadatas":[[{"source_scope":"OTHER999"},{"source_scope":"COURSE123"}]],
    }
    result=ret.search("Purpose of NA NB nonces?",course_id="COURSE123",top_k=1)
    assert [x.chunk_id for x in result]==["right"]
    assert ret._collection.query.call_args.kwargs["where"]=={"course_id":{"$eq":"COURSE123"}}


def test_indexing_preserves_text_quality(monkeypatch,tmp_path):
    from src.api.routes.documents import _bg_index_document
    from src.document_processor import chunker,ingest_corpus
    monkeypatch.setattr(chunker,"extract_and_chunk",lambda _: [
        {"text":"Heading","metadata":{"text_quality":"image_text_sparse"}}])
    collection=Mock()
    monkeypatch.setattr(ingest_corpus,"get_chroma_client",Mock())
    monkeypatch.setattr(ingest_corpus,"get_or_create_collection",lambda _:collection)
    model=Mock(); model.encode.return_value=[[0.]*384]
    monkeypatch.setattr(ingest_corpus,"_load_embedder",lambda:(model,"model",384))
    _bg_index_document(tmp_path/"slides.pdf","COURSE123","doc","job",Mock())
    assert collection.upsert.call_args.kwargs["metadatas"][0]["text_quality"]=="image_text_sparse"


def test_assessment_shorthand_is_generic_and_contextual():
    assert expand_assessment_reference("How many marks is the nonce question in A7 worth?") == \
        "How many marks is the nonce question in Assignment 7 worth?"
    assert expand_assessment_reference("When is a12 due?") == "When is Assignment 12 due?"
    assert expand_assessment_reference("What is A2 paper size?") == "What is A2 paper size?"
    assert expand_assessment_reference("Compare matrix A2 with A3.") == "Compare matrix A2 with A3."


def test_plural_terms_match_without_changing_similarity():
    general=chunk("Assignments and assessment marks.", .6)
    detail=chunk("Analyse the nonces in the protocol (2 marks).", .63)
    assert rerank("nonce mark protocol", [general,detail], .35)[0] is detail


def test_lexical_coverage_rejects_a_mismatched_question_number():
    texts=["Assignment 2 is due tomorrow."]+["Unrelated background."]*20
    assert lexical_candidates("When is Assignment 999 due?",texts)==[]


def test_lexical_branch_recovers_a_candidate_outside_vector_shortlist():
    ret=object.__new__(rp.VectorRetriever)
    ret._model=Mock(); ret._model.encode.return_value=[1.,0.]
    ret._collection=Mock()
    ret._collection.query.return_value={
        "ids":[["overview"]],"documents":[["Assignment 7 overview."]],"distances":[[.55]],
        "metadatas":[[{"source_file":"outline.pdf"}]],
    }
    def get(**kw):
        assert kw["where"]=={"course_id":{"$eq":"COURSE123"}}
        if kw["include"]==["embeddings"]:
            return {"ids":["detail"],"embeddings":[[.3,.953939]]}
        return {"ids":["detail"]+[f"other{i}" for i in range(20)],
                "documents":["Assignment 7: analyse the nonces NA and NB (2 marks)."]+["Unrelated background."]*20,
                "metadatas":[{"source_file":"assignment.pdf","course_id":"COURSE123"}]+[{}]*20}
    ret._collection.get.side_effect=get
    hits=ret.search("Assignment 7 nonces NA NB marks", "COURSE123", top_k=1)
    assert hits[0].chunk_id=="detail" and hits[0].lexical_match
    assert hits[0].similarity==pytest.approx(.3)
    gen=rp.LLMResponseGeneration(Mock(search=Mock(return_value=hits)))
    gen._call_ollama=Mock(return_value=("The task is worth 2 marks [S1].",True))
    result=gen.generate("Assignment 7 nonces NA NB marks","COURSE123")
    assert result.source_refs and result.confidence=="Low" and result.confidence_score==.3


def test_lexical_branch_rechecks_scope_and_avoids_stale_cached_documents():
    ret=object.__new__(rp.VectorRetriever); ret._collection=Mock()
    ret._collection.get.return_value={"ids":["x"],"documents":["Assignment 7 nonces NA NB marks"],
                                      "metadatas":[{"course_id":"OTHER999"}]}
    assert ret._lexical_search("Assignment 7 nonces NA NB marks","COURSE123",[1.,0.])==[]
    ret._collection.get.return_value={"ids":[],"documents":[],"metadatas":[]}
    assert ret._lexical_search("Assignment 7 nonces NA NB marks","COURSE123",[1.,0.])==[]
    assert ret._collection.get.call_count==2


def test_lexical_branch_does_not_admit_a_weak_semantic_match():
    ret=object.__new__(rp.VectorRetriever); ret._collection=Mock()
    ret._collection.get.side_effect=[
        {"ids":["x"],"documents":["Assignment 7 nonce marks"],"metadatas":[{}]},
        {"ids":["x"],"embeddings":[[.05,.99875]]},
    ]
    assert ret._lexical_search("Assignment 7 nonce marks","COURSE123",[1.,0.])==[]
