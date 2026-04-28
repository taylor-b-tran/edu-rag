# Cleanup Review-Ready Checklist

## Scope Lock

- This cleanup covers repository structure and canonical path normalisation for Sprint 3 deliverables.
- Sponsor review deliverable (`Task 19`) is intentionally deferred and was not modified.

## Expected Changed Paths (Allowlist)

- `.gitignore`
- `docs/sprint3_cleanup_matrix.md`
- `docs/cleanup_review_ready_checklist.md`
- `apps/streamlit/main.py`
- `apps/integration/backend/api.py`
- `apps/integration/start.sh`
- `apps/integration/stop.sh`
- `fixtures/sample_responses.json`
- `tests/test_queries.json`
- `data/sample_manifest.md`
- `docs/ui/design_system.md`
- `docs/ui/ui_state.md`
- `docs/ui/assets/paedia_logo_mark.png`
- `docs/ui/wireframes/*.png`
- `docs/architecture/erd_v2_changes.md`
- `docs/architecture/dfd_v2_changes.md`
- `docs/architecture/risk_register_sprint3.md`
- `docs/architecture/storage_sizing.md`
- `docs/architecture/diagrams/*.png`
- `docs/api/api_spec.yaml`
- `docs/api/api_spec_validation.md`
- `docs/api/archive/sprint3_tai_api_specs_original.yaml`
- `docs/governance/privacy_policy.md`
- `docs/governance/ethics_review_sprint3.md`
- `docs/system_design/EduRAG_System_Design_Document_v2.docx`
- `docs/system_design/system_design_document_v2_source.md`
- `docs/meetings/sprint_4_kickoff.md`
- `Team_Contributions/*/README.md`

## Expected Deletions (Old Duplicate Sources)

- `Team_Contributions/Anmoldeep Singh/app/main.py`
- `Team_Contributions/Anmoldeep Singh/fixtures/sample_responses.json`
- `Team_Contributions/Anmoldeep Singh/docs/design_system.md`
- `Team_Contributions/Anmoldeep Singh/docs/ui_state.md`
- `Team_Contributions/Anmoldeep Singh/docs/assets/paedia_logo_mark.png`
- `Team_Contributions/Anmoldeep Singh/docs/wireframes/*.png`
- `Team_Contributions/Namaratne/docs/*.md`
- `Team_Contributions/Namaratne/diagrams/*.png`

## Denylist (Should Not Change In This Cleanup)

- `docs/meetings/sprint3_sponsor_review.docx`
- `docs/meetings/sprint3_*.docx` (other than existing files already in develop)
- `src/**`
- `db/**`
- `notebooks/**`
- `materials/**`
- unrelated project requirements files

## Validation Snapshot

- `tests/test_queries.json` parses successfully and contains 31 entries.
- `docs/api/api_spec.yaml` parses as OpenAPI `3.0.3` with 15 paths.
- Integration files exist under canonical path `apps/integration/`.
