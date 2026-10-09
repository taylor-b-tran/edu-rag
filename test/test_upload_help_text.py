"""The uploader's help text names only the file types it accepts.

The picker accepted PDF, PPTX and DOCX, but its tooltip also advertised TXT
and MD, which the API refuses.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402
from src.document_processor.chunker import SUPPORTED_EXTENSIONS  # noqa: E402

MAIN = Path(main.__file__)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z]+", text))


def test_help_names_only_the_types_the_uploader_accepts():
    words = _words(main._upload_help_text())
    assert {"PDF", "PPTX", "DOCX"} <= words
    assert not ({"TXT", "MD"} & words)


def test_uploader_types_match_the_api():
    assert {"." + t for t in main._UPLOAD_TYPES} == SUPPORTED_EXTENSIONS


def test_help_states_the_limit_the_page_enforces():
    assert f"{main.MAX_UPLOAD_MB} MB" in main._upload_help_text()


def test_no_literal_uploader_help_mentions_txt_or_md():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "file_uploader":
            for kw in node.keywords:
                if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                    assert not ({"TXT", "MD"} & _words(str(kw.value.value)))
