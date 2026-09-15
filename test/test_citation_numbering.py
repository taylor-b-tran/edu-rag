"""Citation markers must point at the list the reader is actually shown.

The prompt numbers retrieved chunks S1..Sk. The answer is then filtered to the
chunks the model cited, and that list is de-duplicated by file and page. Both
steps shorten the list, and neither used to touch the answer text -- so an
answer could say "[S5]" beside a two-item source list, where the item that had
been S5 was displayed as 2.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.rag_pipeline import (  # noqa: E402
    LLMResponseGeneration,
    RetrievedChunk,
)

# The helpers are imported inside the two tests that exercise them directly, so
# that the behavioural tests above still run -- and still fail -- against a
# build where those helpers do not exist yet.


class _StubRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    def search(self, query, *a, **kw):
        return self._chunks


def chunk(i, source_file, page):
    return RetrievedChunk(
        chunk_id=f"c{i}", text=f"text {i}", source_file=source_file,
        page_number=page, topic="Topic", week="3", distance=0.1 * i,
    )


def answer_with(raw, chunks):
    gen = LLMResponseGeneration(retriever=_StubRetriever(chunks))
    gen._call_ollama = lambda prompt, chunks=None, **kw: (raw, True)
    return gen.generate("q")


@pytest.fixture
def five():
    return [chunk(i, f"Week{i}.pdf", i) for i in range(1, 6)]


# --- the defect itself --------------------------------------------------

def test_a_marker_never_points_past_the_end_of_the_list(five):
    r = answer_with("Scoping uses course_id [S1]. The filter is MongoDB-style [S5].", five)
    assert len(r.source_refs) == 2
    assert "[S2]" in r.answer
    assert "[S5]" not in r.answer


def test_the_renumbered_marker_names_the_source_it_meant(five):
    r = answer_with("First [S1]. Fifth [S5].", five)
    # [S2] is the second entry, and the second entry is the chunk that was S5.
    assert r.source_refs[1]["source_file"] == "Week5.pdf"


def test_two_chunks_from_one_page_collapse_to_one_number():
    """De-duplication shrinks the list a second time, after the filter."""
    chunks = [chunk(1, "Week1.pdf", 7), chunk(2, "Week2.pdf", 3), chunk(3, "Week1.pdf", 7)]
    r = answer_with("First point [S1]. Third point [S3].", chunks)
    assert len(r.source_refs) == 1
    assert r.answer.count("[S1]") == 2
    assert "[S3]" not in r.answer


def test_citations_already_contiguous_are_left_alone(five):
    r = answer_with("First [S1]. Second [S2].", five)
    assert "[S1]" in r.answer and "[S2]" in r.answer
    assert len(r.source_refs) == 2


def test_the_sources_line_is_renumbered_and_deduplicated(five):
    r = answer_with("Body [S1] and [S5].\n\nSources: S1, S5", five)
    line = [ln for ln in r.answer.splitlines() if ln.lower().startswith("sources:")]
    assert line == ["Sources: S1, S2"]


def test_dedup_does_not_leave_the_sources_line_repeating_itself():
    chunks = [chunk(1, "Week1.pdf", 7), chunk(2, "Week1.pdf", 7)]
    r = answer_with("A [S1]. B [S2].\n\nSources: S1, S2", chunks)
    line = [ln for ln in r.answer.splitlines() if ln.lower().startswith("sources:")]
    assert line == ["Sources: S1"]


def test_uncited_answers_still_get_numbering_that_matches_the_list():
    """Nothing extractable, so every chunk is listed -- but de-duplication can
    still shrink that list, and the markers have to follow it."""
    chunks = [chunk(1, "Week1.pdf", 2), chunk(2, "Week1.pdf", 2), chunk(3, "Week9.pdf", 1)]
    gen = LLMResponseGeneration(retriever=_StubRetriever(chunks))
    gen._call_ollama = lambda prompt, chunks=None, **kw: ("No markers at all here.", True)
    r = gen.generate("q")
    assert len(r.source_refs) == 2
    assert "[S3]" not in r.answer


# --- the grouped form models actually emit ------------------------------

def test_a_grouped_marker_is_split_before_anything_else_sees_it():
    from src.document_processor.rag_pipeline import _split_citation_groups
    assert _split_citation_groups("as shown [S1, S3]") == "as shown [S1][S3]"
    assert _split_citation_groups("tight [S2,S4]") == "tight [S2][S4]"
    assert _split_citation_groups("single [S1]") == "single [S1]"
    assert _split_citation_groups("not a citation [Section 3]") == "not a citation [Section 3]"


def test_a_grouped_marker_is_renumbered_like_any_other(five):
    r = answer_with("Grouped [S1, S3]. Lone [S5].", five)
    assert len(r.source_refs) == 3
    assert "[S1][S2]" in r.answer
    assert "[S3]" in r.answer
    assert "[S1, S3]" not in r.answer


# --- the helper on its own ----------------------------------------------

def test_a_marker_with_nowhere_to_point_is_dropped_not_left_dangling():
    from src.document_processor.rag_pipeline import _renumber_citations
    out = _renumber_citations("Kept [S1]. Orphan [S4].", {1: 1})
    assert "[S1]" in out
    assert "S4" not in out


def test_renumbering_leaves_the_prose_intact():
    from src.document_processor.rag_pipeline import _renumber_citations
    out = _renumber_citations("Backprop uses the chain rule [S2].", {2: 1})
    assert out == "Backprop uses the chain rule [S1]."
