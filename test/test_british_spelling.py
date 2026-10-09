"""User-visible text uses British spelling.

The interface already says "Summarise" and "Enrolment failed.", but four
strings on the Admin Dashboard said "Enroll" and "Enrollments", so the same
screen mixed two spellings. UOW is in Australia, so the rule is British
throughout.

The check reads every string constant in main.py except docstrings, so
comments, identifiers and CSS keywords such as `color` are never flagged. The
deny list is explicit on purpose, so that words like "size" cannot trip it.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "apps" / "streamlit" / "main.py"

# "enrolled" and "enrolling" are correct in both spellings and are not listed.
AMERICAN = re.compile(
    r"\benroll(s|ment|ments)?\b"
    r"|\b(summariz|organiz|customiz|normaliz|authoriz)\w*"
    r"|\b(behavior|favorite)s?\b",
    re.IGNORECASE,
)


def _is_docstring(body) -> ast.expr | None:
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value
    return None


def user_text_constants():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = _is_docstring(node.body)
            if doc is not None:
                docstrings.add(id(doc))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings):
            yield node.lineno, node.value


def test_no_american_spelling_in_user_visible_strings():
    offenders = [
        (line, match.group(0))
        for line, text in user_text_constants()
        for match in AMERICAN.finditer(text)
    ]
    assert not offenders, f"American spellings in main.py: {offenders}"


def test_the_check_would_catch_a_regression():
    # Guards the guard: the pattern must flag the forms we removed, and must
    # leave the forms that are correct in both spellings alone.
    for bad in ("Enroll", "Failed to enroll member.", "Courses & Enrollments", "Summarize it"):
        assert AMERICAN.search(bad), bad
    for good in ("Enrol", "Failed to enrol member.", "Courses & Enrolments",
                 "You are not enrolled in any course yet.", "Enrolment failed.", "Summarise it"):
        assert not AMERICAN.search(good), good
