import secrets
from unittest.mock import Mock

import pytest

from scripts import check_demo_ready as ready


@pytest.mark.parametrize("answer, fallback, expected, reason", [
    ("This cannot be verified from the available course materials [S1].", False, ready.FAIL, "do not cover"),
    ("THIS CANNOT BE VERIFIED FROM THE AVAILABLE COURSE MATERIALS [S1].", False, ready.FAIL, "do not cover"),
    ("This cannot be verified\nfrom the available  course material [S1].", False, ready.FAIL, "do not cover"),
    ("[Ollama not running] Start the service [S1]", False, ready.FAIL, "outage hint"),
    ("[Ollama response timed out. Try again.] [S1]", False, ready.FAIL, "outage hint"),
    ("[LLM Error: unavailable] [S1]", False, ready.FAIL, "outage hint"),
    ("Based on general knowledge\n\n[LLM Error: unavailable] [S1]", False, ready.FAIL, "outage hint"),
    ("[LLM Error: unavailable]", True, ready.FAIL, "FALLBACK"),
    ("A decision tree branches on feature values.", False, ready.FAIL, "no inline source citation"),
    ("A decision tree branches on feature values [S1].", False, ready.PASS, "grounded answer"),
    ("[S1] A decision tree branches on feature values.", False, ready.PASS, "grounded answer"),
])
def test_readiness_requires_a_grounded_answer(monkeypatch, answer, fallback, expected, reason):
    monkeypatch.setattr(ready, "DEMO_STUDENT_PASSWORD", secrets.token_urlsafe())
    post = Mock(side_effect=[
        (200, {"access_token": "test-token"}, ""),
        (200, {"answer": answer, "is_fallback": fallback,
               "source_references": [{"source_file": "lecture.pdf"}]}, ""),
    ])
    monkeypatch.setattr(ready, "_http_post_json", post)
    status, detail = ready.check_demo_question()
    assert status == expected
    assert reason in detail
    if expected == ready.FAIL:
        assert repr(answer[:150]) in detail


def test_default_question_is_decision_tree(monkeypatch):
    import importlib
    monkeypatch.delenv("PAEDIA_DEMO_QUESTION", raising=False)
    assert importlib.reload(ready).DEMO_QUESTION == "What is a decision tree?"
