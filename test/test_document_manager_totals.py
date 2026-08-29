"""The Document Manager summary line, against documents that failed to index.

Opening Document Manager on the shared host raised:

    TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
    apps/streamlit/main.py, in _render_document_table

`chunks` is NULL for anything that failed to index - 69 of the 72 rows on the
host at the time - and `.get("chunks", 0)` returns that None rather than the
default, because the key is present and only its value is missing. The sum then
blew up and took the entire page with it, so a single failed upload hid every
document that had worked.

That matters beyond the test rubbish that triggered it: any real user who
uploads a corrupt or unreadable PDF loses the whole page, which is exactly what
T8-36 is meant to catch.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/workspace/apps/streamlit")


@pytest.fixture(scope="module")
def totals():
    """main.py imports outside a Streamlit runtime; it only warns."""
    import main
    return main._document_totals


def test_a_failed_document_does_not_break_the_count(totals):
    docs = [
        {"status": "indexed", "chunks": 37},
        {"status": "failed", "chunks": None},
    ]
    assert totals(docs) == (1, 37)


def test_every_document_failed(totals):
    """The state the host was actually in."""
    docs = [{"status": "failed", "chunks": None} for _ in range(69)]
    assert totals(docs) == (0, 0)


def test_a_missing_key_still_works(totals):
    assert totals([{"status": "indexed"}]) == (1, 0)


def test_completed_counts_as_indexed(totals):
    docs = [{"status": "completed", "chunks": 5}, {"status": "indexed", "chunks": 5}]
    assert totals(docs) == (2, 10)


def test_status_absent_is_not_counted_as_indexed(totals):
    assert totals([{"chunks": 3}]) == (0, 3)


def test_no_documents(totals):
    assert totals([]) == (0, 0)


def test_chunks_are_summed_across_a_mixed_list(totals):
    docs = [
        {"status": "indexed", "chunks": 10},
        {"status": "failed", "chunks": None},
        {"status": "processing", "chunks": None},
        {"status": "completed", "chunks": 4},
    ]
    assert totals(docs) == (2, 14)
