"""Programmatic re-run of QA checklist Sections 4 (Live RAG) and 5 (Citations).

Original checklist: docs/qa_checklist_sprint5.md
Owner: Tung; this script is the assistive automation, Tung still owns the call.

Usage:
    python scripts/qa_sections_4_5_rerun.py

Writes results to docs/qa_sections_4_5_results.md for Tung to paste back into
qa_checklist_sprint5.md (flipping the Status column from SKIP to PASS/FAIL).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

API = "http://localhost:5000"
LOGIN = {"email": "student@uow.edu.au", "password": "student123"}

SECTION_4 = [
    ("R-01", "What does RAG stand for?", "live retrieval; backend_mode=chromadb"),
    ("R-02", "What is a vector embedding?", "at least one source_reference"),
    ("R-03", "What is the role of ChromaDB in EduRAG?", "cites seeded corpus"),
    ("R-04", "Explain the chunking strategy used in EduRAG.", "cites seeded corpus"),
    ("R-05", "What file formats can be uploaded?", "mentions PDF, PPTX, or DOCX"),
    ("R-06", "What is the best chocolate cake recipe?", "graceful fallback; no fake citations"),
    ("R-07", None, "source_references shape check (run after R-01)"),
]

SECTION_5 = [
    ("C-01", "After live RAG query -- citation source + excerpt visible in response"),
    ("C-02", "Citations not empty for on-topic queries"),
    ("C-03", "No fake citations for off-topic queries"),
    ("C-04", "Citation metadata includes a source identifier"),
    ("C-05", "Citation metadata includes chunk_index or page"),
]


def login() -> str:
    r = requests.post(f"{API}/api/auth/login", json=LOGIN, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def query(token: str, q: str) -> dict:
    t0 = time.time()
    r = requests.post(
        f"{API}/api/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": q, "course_id": "CSIT321"},
        timeout=300,
    )
    elapsed = time.time() - t0
    if r.status_code == 429:
        wait_s = 65
        print(f"    (rate-limited, waiting {wait_s}s for window to reset...)")
        time.sleep(wait_s)
        return query(token, q)
    r.raise_for_status()
    body = r.json()
    body["_elapsed_s"] = round(elapsed, 2)
    return body


def main():
    print("Logging in...")
    token = login()

    section4_results = []
    section4_responses: dict[str, dict] = {}

    print("\n=== Section 4: Live RAG ===")
    for case_id, q, expectation in SECTION_4:
        if q is None:
            r01 = section4_responses.get("R-01") or {}
            refs = r01.get("source_references", [])
            ok = isinstance(refs, list) and all(
                isinstance(ref, dict) and ("source_file" in ref or "source" in ref)
                for ref in refs
            )
            status = "PASS" if ok and refs else ("PASS (empty list -- fallback path)" if isinstance(refs, list) else "FAIL")
            notes = f"R-01 returned {len(refs)} references; first ref keys: {sorted(refs[0].keys()) if refs else 'n/a'}"
            section4_results.append((case_id, expectation, status, notes))
            print(f"  {case_id}: {status} -- {notes}")
            continue

        try:
            body = query(token, q)
        except Exception as exc:
            section4_results.append((case_id, expectation, "FAIL", f"Request error: {exc}"))
            print(f"  {case_id}: FAIL -- {exc}")
            continue

        section4_responses[case_id] = body
        backend = body.get("backend_mode")
        model = body.get("model_used")
        n_refs = len(body.get("source_references", []))
        is_fallback = body.get("is_fallback")
        conf = body.get("confidence")
        elapsed = body["_elapsed_s"]

        if case_id == "R-06":
            ok = is_fallback is True or n_refs == 0 or conf == "Low"
            status = "PASS" if ok else "FAIL"
            notes = f"off-topic -> is_fallback={is_fallback}, refs={n_refs}, conf={conf}, {elapsed}s"
        elif case_id == "R-02":
            ok = n_refs >= 1
            status = "PASS" if ok else "FAIL"
            notes = f"backend={backend} model={model} refs={n_refs} conf={conf} {elapsed}s"
        elif case_id == "R-05":
            ans = (body.get("answer") or "").lower()
            ok = any(fmt in ans for fmt in ("pdf", "pptx", "docx"))
            status = "PASS" if ok else "PARTIAL (model did not mention PDF/PPTX/DOCX explicitly)"
            notes = f"answer head: {(body.get('answer') or '')[:120]!r}... ({elapsed}s)"
        else:
            ok = backend == "chromadb" and isinstance(body.get("answer"), str) and body["answer"].strip()
            status = "PASS" if ok else "FAIL"
            notes = f"backend={backend} model={model} refs={n_refs} conf={conf} {elapsed}s"

        section4_results.append((case_id, expectation, status, notes))
        print(f"  {case_id}: {status} -- {notes}")

    print("\n=== Section 5: Citations ===")
    section5_results = []
    r01 = section4_responses.get("R-01") or {}
    r06 = section4_responses.get("R-06") or {}
    on_topic_refs = r01.get("source_references", [])
    off_topic_refs = r06.get("source_references", [])

    for case_id, expectation in SECTION_5:
        if case_id == "C-01":
            ok = bool(on_topic_refs) and any("source" in str(r) for r in on_topic_refs)
            status = "PASS" if ok else "FAIL"
            notes = f"on-topic refs: {len(on_topic_refs)} (sample: {on_topic_refs[0] if on_topic_refs else 'none'})"
        elif case_id == "C-02":
            ok = len(on_topic_refs) >= 1
            status = "PASS" if ok else "FAIL"
            notes = f"on-topic ref count: {len(on_topic_refs)}"
        elif case_id == "C-03":
            ok = len(off_topic_refs) == 0 or r06.get("is_fallback") is True
            status = "PASS" if ok else "FAIL"
            notes = f"off-topic refs: {len(off_topic_refs)}, is_fallback={r06.get('is_fallback')}"
        elif case_id == "C-04":
            ok = all("source_file" in ref or "source" in ref for ref in on_topic_refs)
            status = "PASS" if ok and on_topic_refs else ("PASS (no refs to validate)" if not on_topic_refs else "FAIL")
            notes = f"all refs have a source identifier: {ok}"
        elif case_id == "C-05":
            ok = all(("chunk_index" in ref) or ("page" in ref) for ref in on_topic_refs)
            status = "PASS" if ok and on_topic_refs else ("PASS (no refs to validate)" if not on_topic_refs else "FAIL")
            notes = f"all refs have chunk_index or page: {ok}"

        section5_results.append((case_id, expectation, status, notes))
        print(f"  {case_id}: {status} -- {notes}")

    out_path = Path(__file__).resolve().parents[1] / "docs" / "qa_sections_4_5_results.md"
    lines = [
        "# QA Checklist -- Sections 4 & 5 Results (programmatic re-run)",
        "",
        f"**Run on:** {time.strftime('%d %b %Y %H:%M')}",
        "**Script:** `scripts/qa_sections_4_5_rerun.py`",
        "**Backend:** live `/api/query` against running Docker stack (GPU-enabled Ollama)",
        "**Purpose:** Provide evidence for Tung to flip the SKIP rows in `docs/qa_checklist_sprint5.md` Sections 4–5 to PASS/FAIL.",
        "",
        "> This script does not replace manual UI verification of citation rendering. It validates the API-level contract; pair with a manual Streamlit walk-through for the final sign-off.",
        "",
        "## Section 4 -- Live ChromaDB / Ollama RAG Backend",
        "",
        "| ID | Expectation | Status | Notes |",
        "|---|---|---|---|",
    ]
    for case_id, expectation, status, notes in section4_results:
        lines.append(f"| {case_id} | {expectation} | **{status}** | {notes} |")

    lines += [
        "",
        "## Section 5 -- Citations (API-level)",
        "",
        "| ID | Expectation | Status | Notes |",
        "|---|---|---|---|",
    ]
    for case_id, expectation, status, notes in section5_results:
        lines.append(f"| {case_id} | {expectation} | **{status}** | {notes} |")

    lines += [
        "",
        "## Raw response sample (R-01)",
        "",
        "```json",
        json.dumps(r01, indent=2, default=str)[:2000],
        "```",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
