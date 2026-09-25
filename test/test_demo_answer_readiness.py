import secrets
from unittest.mock import Mock

import pytest

from scripts import check_demo_ready as ready


@pytest.mark.parametrize("answer, expected", [
    ("This cannot be verified from the available course materials.", ready.FAIL),
    ("[Ollama not running] Start the service", ready.FAIL),
    ("[LLM Error: unavailable]", ready.FAIL),
    ("A decision tree branches on feature values.", ready.FAIL),
    ("A decision tree branches on feature values [S1].", ready.PASS),
])
def test_readiness_requires_a_grounded_answer(monkeypatch, answer, expected):
    monkeypatch.setattr(ready, "DEMO_STUDENT_PASSWORD", secrets.token_urlsafe())
    post = Mock(side_effect=[
        (200, {"access_token": "test-token"}, ""),
        (200, {"answer": answer, "is_fallback": False,
               "source_references": [{"source_file": "lecture.pdf"}]}, ""),
    ])
    monkeypatch.setattr(ready, "_http_post_json", post)
    assert ready.check_demo_question()[0] == expected


def test_default_question_is_covered(monkeypatch):
    import importlib
    monkeypatch.delenv("PAEDIA_DEMO_QUESTION", raising=False)
    assert importlib.reload(ready).DEMO_QUESTION == "What is a decision tree?"
