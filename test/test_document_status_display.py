"""The Document Manager has to tell the truth about a document, and fit on screen.

Two defects this guards against:

* A document rendered a green **Indexed** badge while holding zero chunks in
  the vector store. It could never be cited, the landing screen advertised a
  prompt naming it, and nothing on screen said otherwise.
* At narrow widths the Status column was too small for the word "Indexed" --
  it wrapped to one character per line and stretched the row -- and the
  Actions column was too small for its buttons, which overflowed their cell.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


# --- status truthfulness -------------------------------------------------

def test_indexed_with_chunks_reads_as_indexed():
    label, badge, note = main._document_status({"status": "indexed", "chunks": 79})
    assert label == "indexed"
    assert badge == "badge-indexed"
    assert "79" in note


def test_indexed_with_no_chunks_does_not_claim_to_be_indexed():
    """The shape of a row that sits in the corpus looking healthy."""
    label, badge, note = main._document_status(
        {"status": "indexed", "chunks": None, "indexing_status": None})
    assert label != "indexed"
    assert badge != "badge-indexed"
    assert "re-upload" in note.lower()
    # Short enough to fit the Status cell at 966px, where the longer wording
    # overran into the Uploaded column.
    assert len(label) <= 11


def test_zero_chunks_is_treated_the_same_as_none():
    label, badge, _ = main._document_status({"status": "completed", "chunks": 0})
    assert label != "indexed"
    assert badge != "badge-indexed"


def test_processing_and_pending_are_reported_as_themselves():
    assert main._document_status({"status": "processing"})[0] == "processing"
    assert main._document_status({"status": "processing"})[1] == "badge-processing"
    assert main._document_status({"status": "pending"})[0] == "pending"


def test_a_row_with_no_status_at_all_is_pending_not_indexed():
    label, badge, _ = main._document_status({})
    assert label == "pending"
    assert badge != "badge-indexed"


def test_a_failed_row_keeps_its_own_word():
    label, badge, _ = main._document_status({"status": "failed", "chunks": 0})
    assert label == "failed"
    assert badge == "badge-failed"


def test_indexing_status_is_used_when_status_is_absent():
    label, _, _ = main._document_status({"indexing_status": "processing"})
    assert label == "processing"


# --- layout --------------------------------------------------------------

def test_status_and_actions_get_more_than_a_tenth_of_the_row():
    """Too small a share leaves no room for the word "Indexed", which then
    wraps one character per line."""
    ratio = main._document_table_ratio(student_view=False)
    assert len(ratio) == 7
    status_share, actions_share = ratio[3], ratio[5]
    assert status_share > 1
    assert actions_share > 1


def test_a_student_gets_an_open_column_but_no_remove_column():
    """A list a student cannot open has no reason to exist. Opening is for
    everyone; removing stays with the lecturer."""
    student = main._document_table_ratio(student_view=True)
    lecturer = main._document_table_ratio(student_view=False)
    assert len(student) == 6
    assert len(lecturer) == 7
    assert lecturer[:6] == student


def test_header_and_row_are_laid_out_on_the_same_ratio():
    """They were two separate literals; changing one and not the other would
    misalign every header from its column."""
    assert (main._document_table_ratio(False) == main._document_table_ratio(False))
    assert main._document_table_ratio(True) == main._document_table_ratio(False)[:6]


# --- the fallback notice -------------------------------------------------

def test_the_fallback_sentence_is_stripped_before_the_banner_is_drawn():
    body = ("Based on general knowledge — not verified against course materials.\n\n"
            "Neural networks learn by adjusting weights.")
    out = main._strip_fallback_prefix(body)
    assert out == "Neural networks learn by adjusting weights."


def test_a_hyphen_instead_of_an_em_dash_is_still_stripped():
    body = "Based on general knowledge - not verified against course materials.\n\nBody."
    assert main._strip_fallback_prefix(body) == "Body."


def test_an_ordinary_answer_is_left_exactly_as_it_was():
    body = "Retrieval is scoped by course_id [S1]."
    assert main._strip_fallback_prefix(body) == body


def test_stripping_an_empty_answer_does_not_raise():
    assert main._strip_fallback_prefix("") == ""
    assert main._strip_fallback_prefix(None) is None


# --- the summary line must agree with the badges -------------------------

def test_the_summary_counts_the_same_way_the_badge_decides():
    """The table read "No chunks" on a row while the line beneath it counted
    that row as indexed, because the two used different rules."""
    docs = [
        {"status": "indexed", "chunks": 79},
        {"status": "indexed", "chunks": None},   # the badge calls this not indexed
        {"status": "processing", "chunks": 0},
    ]
    indexed, total_chunks = main._document_totals(docs)
    assert indexed == 1
    assert total_chunks == 79


def test_a_null_chunk_count_does_not_crash_the_summary():
    """One failed upload used to take the whole page down with a TypeError."""
    assert main._document_totals([{"status": "failed", "chunks": None}]) == (0, 0)


# --- suggested prompts ---------------------------------------------------

class _FakeApi:
    def __init__(self, docs): self._docs = docs
    def get_documents(self, course_id=None): return self._docs


def test_a_prompt_never_names_a_document_that_cannot_be_cited(monkeypatch):
    """The landing screen offered a "Summarise ..." prompt for a document
    holding no chunks, so the answer came from unrelated material and nothing
    on screen said so."""
    monkeypatch.setattr(main, "api", _FakeApi([
        {"original_filename": "RAG_Pipeline_Overview.pdf", "chunks": None},
        {"original_filename": "NNDesign.pdf", "chunks": 1965},
    ]))
    monkeypatch.setattr(main, "st", _FakeState({"course_id": "CSIT321"}))

    prompts = main.get_suggested_prompts()
    assert not any("RAG_Pipeline_Overview" in p for p in prompts)
    assert any("NNDesign" in p for p in prompts)


def test_no_retrievable_document_means_no_summarise_prompt(monkeypatch):
    monkeypatch.setattr(main, "api", _FakeApi([
        {"original_filename": "Broken.pdf", "chunks": 0},
    ]))
    monkeypatch.setattr(main, "st", _FakeState({"course_id": "CSIT321"}))

    prompts = main.get_suggested_prompts()
    assert not any(p.startswith("Summarise") for p in prompts)
    assert any("CSIT321" in p for p in prompts)


class _FakeState:
    """Just enough of st for get_suggested_prompts: a session_state dict."""
    def __init__(self, initial):
        self.session_state = dict(initial)


def test_every_place_that_counts_indexed_uses_the_same_rule():
    """The table, the summary line, the sidebar and the chat header each had
    their own rule, so one course was reported as 7 indexed in one place and 6
    in another on the same screen."""
    docs = [
        {"status": "indexed", "chunks": 79},
        {"status": "indexed", "chunks": None},
        {"status": "completed", "chunks": 0},
        {"status": "processing", "chunks": None},
    ]
    by_rule = main._document_indexed_count(docs)
    by_badge = sum(1 for d in docs if main._document_status(d)[0] == "indexed")
    by_summary = main._document_totals(docs)[0]
    assert by_rule == by_badge == by_summary == 1


def test_counting_survives_an_empty_or_missing_list():
    assert main._document_indexed_count([]) == 0
    assert main._document_indexed_count(None) == 0


def test_the_tooltip_does_not_claim_to_have_read_the_vector_store():
    """It reads the count stored with the document, which is not the same
    thing as looking in ChromaDB."""
    _, _, note = main._document_status({"status": "indexed", "chunks": 79})
    assert "vector store" not in note.lower()
    assert "79" in note


# --- an upload that is still waiting is not a failed upload -----------------

from datetime import datetime, timedelta, timezone  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402


def _uploaded(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def test_a_queued_upload_is_waiting_not_failed():
    label, badge, _ = main._document_status({"status": "queued", "chunks": None})
    assert label == "queued"
    assert badge == "badge-pending"


def test_indexing_status_queued_is_waiting_too():
    assert main._document_status({"indexing_status": "queued"})[1] == "badge-pending"


def test_a_recent_processing_row_is_neutral():
    doc = {"status": "processing", "chunks": None, "uploaded_at": _uploaded(2)}
    assert main._document_status(doc)[1] == "badge-processing"


@pytest.mark.parametrize("status", ["queued", "pending", "processing"])
def test_a_row_waiting_past_the_limit_is_shown_as_stalled(status):
    doc = {"status": status, "chunks": None, "uploaded_at": _uploaded(main._STALLED_AFTER_MINUTES + 5)}
    label, badge, note = main._document_status(doc)
    assert (label, badge) == ("stalled", "badge-failed")
    assert len(label) <= 11
    assert "re-upload" in note.lower()


def test_a_row_without_a_timestamp_is_never_called_stalled():
    assert main._document_status({"status": "queued"})[0] == "queued"
    assert main._document_status({"status": "queued", "uploaded_at": "not a date"})[0] == "queued"


def test_sidebar_dot_is_not_red_for_work_in_progress():
    assert main._document_status_dot({"status": "queued", "chunks": None}) != "#EF4444"
    assert main._document_status_dot({"status": "processing", "chunks": None}) != "#EF4444"
    assert main._document_status_dot({"status": "failed"}) == "#EF4444"
    assert main._document_status_dot({"status": "indexed", "chunks": 5}) == "#10B981"
    assert main._document_status_dot({"status": "queued", "uploaded_at": _uploaded(60)}) == "#EF4444"


class _State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def test_reupload_warning_skips_uploads_still_in_progress(monkeypatch):
    st = MagicMock()
    st.session_state = _State(user={"role": "Lecturer", "name": "L", "enrolled_courses": ["TEST101"]},
                              course_options=["TEST101"], course_id="TEST101")
    st.columns.side_effect = lambda spec, **kw: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
    st.button.return_value = False
    api = MagicMock()
    api.get_documents.return_value = [
        {"document_id": "d1", "original_filename": "week1.pdf", "status": "queued", "chunks": None},
        {"document_id": "d2", "original_filename": "broken.pdf", "status": "failed", "chunks": None},
    ]
    monkeypatch.setattr(main, "st", st)
    monkeypatch.setattr(main, "api", api)
    main._render_document_table(student_view=False)
    warning = " ".join(str(c.args[0]) for c in st.warning.call_args_list)
    assert "broken.pdf" in warning
    assert "week1.pdf" not in warning
