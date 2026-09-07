"""
T8-12 — Full regression across everything that changed (Sprint 8).

Owner: Tung Phuong Anh Huynh
Sprint: 8 (18 Aug - 1 Sep 2026)

This file locks in two real regressions found while doing the T8-12 pass,
so neither can silently come back:

1. db/seed/development.sql had a missing comma in the `courses` VALUES list
   (introduced alongside T8-13's CSIT214/CSCI369/MATH202 rows), which broke
   the entire seed script since it is wrapped in one BEGIN...COMMIT
   transaction. Caught here by parsing every seed/migration .sql file with
   pglast - a real Postgres-grammar parser - instead of eyeballing them, and
   without needing a live Postgres instance (there isn't one in CI).

2. (T9-18 correction) .github/workflows/ci.yml's "Validate JSON artifacts"
   step lists docs/rag_config_benchmark_2026-04-22.json and
   docs/rag_config_benchmark_31q.json. A T8-12 note here previously claimed
   these "do not exist anywhere in the repo" - that was wrong. Both files
   have been committed since April/May 2026; they're only marked
   `export-ignore` in .gitattributes, which trims them from `git archive`/
   zip exports, not from the actual repo that CI checks out. The tests below
   still guard against real drift (a file referenced in CI genuinely being
   renamed/deleted without CI being updated) by parsing the same
   `paths = [...]` block CI runs and asserting every path it lists exists in
   this checkout, so that class of bug fails locally and in review, not
   silently in Actions.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# T9-18: this used to be a module-level `pytest.importorskip("pglast")`,
# which skipped every test in this file - including
# test_ci_json_artifact_paths_all_exist and test_ci_json_artifact_paths_are_
# valid_json, neither of which touches pglast - whenever pglast wasn't
# installed. Import it defensively instead, and only skip the one test that
# actually needs it (below), so a missing dependency no longer hides the
# CI-artifact-path checks too.
try:
    import pglast
except ImportError:
    pglast = None

REPO_ROOT = Path(__file__).resolve().parents[1]

_SQL_FILES = sorted(
    list((REPO_ROOT / "db" / "seed").glob("*.sql"))
    + list((REPO_ROOT / "db" / "migrations").glob("*.sql"))
)


@pytest.mark.skipif(
    pglast is None, reason="pglast not installed - see requirements-dev.txt"
)
@pytest.mark.parametrize("sql_path", _SQL_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_seed_and_migration_sql_files_parse_cleanly(sql_path: Path):
    """Every committed seed/migration file must be valid Postgres SQL.

    Regression case: db/seed/development.sql previously failed here with
    "syntax error at or near '(' " at the line where the T8-13 CSIT214 row
    followed the CSIT321 row without a separating comma.
    """
    sql_text = sql_path.read_text(encoding="utf-8")
    try:
        statements = pglast.parse_sql(sql_text)
    except Exception as exc:  # pglast raises its own ParseError subclass
        pytest.fail(f"{sql_path.relative_to(REPO_ROOT)} failed to parse: {exc}")
    assert statements, f"{sql_path.relative_to(REPO_ROOT)} parsed to zero statements"


def test_at_least_one_sql_file_was_actually_checked():
    """Guards against the parametrized test above silently checking nothing
    if db/seed or db/migrations is ever renamed."""
    assert _SQL_FILES, "expected at least one .sql file under db/seed or db/migrations"


def _ci_json_artifact_paths() -> list[str]:
    """Extract the `paths = [...]` list from ci.yml's "Validate JSON
    artifacts" step without needing a YAML/heredoc parser - the step embeds
    a Python heredoc, and PyYAML would hand back that heredoc as one opaque
    string anyway. A small regex plus ast.literal_eval on just the list
    literal is more reliable than reimplementing shell/YAML parsing here.
    """
    ci_yml = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    match = re.search(r"paths\s*=\s*(\[[^\]]*\])", ci_yml, re.DOTALL)
    assert match, "could not find `paths = [...]` in ci.yml's JSON validation step"
    # Each entry looks like Path("some/file.json") - strip the Path(...) wrapper
    # so ast.literal_eval sees a plain list of string literals.
    list_src = re.sub(r"Path\(([^)]*)\)", r"\1", match.group(1))
    return ast.literal_eval(list_src)


def test_ci_json_artifact_paths_all_exist():
    """Every file CI's 'Validate JSON artifacts' step checks must exist.

    Guards against a file referenced in ci.yml's paths list being renamed or
    deleted without ci.yml being updated. (It does not guard against
    export-ignore in .gitattributes trimming a file from a zip export - that
    is expected and is not a bug; see the module docstring and the T9-18
    correction to ci.yml's comment above.)
    """
    paths = _ci_json_artifact_paths()
    assert paths, "expected at least one path in ci.yml's JSON validation list"
    missing = [p for p in paths if not (REPO_ROOT / p).exists()]
    assert not missing, (
        f"ci.yml references JSON artifact(s) that do not exist in the repo: {missing}"
    )


def test_ci_json_artifact_paths_are_valid_json():
    """Belt-and-braces: also actually parse them, matching what CI itself
    does, so a syntactically-present-but-corrupt JSON file fails locally."""
    import json

    for rel_path in _ci_json_artifact_paths():
        path = REPO_ROOT / rel_path
        with path.open(encoding="utf-8") as handle:
            json.load(handle)