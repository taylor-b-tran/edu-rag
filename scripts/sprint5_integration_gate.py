from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
TEXT_SUFFIXES = {
    ".css",
    ".env",
    ".html",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}
REQUIRED_SERVICES = {"postgres", "chromadb", "ollama", "api", "streamlit"}
FORBIDDEN_TRACKED_PREFIXES = (
    "itegration/",
    "data/samples/",
    ".agents/",
    ".ai/",
)


def _run_git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_text_path(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIXES


def check_no_conflict_markers(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for rel_path in paths:
        if not _is_text_path(rel_path):
            continue
        path = REPO_ROOT / rel_path
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            errors.append(f"{rel_path}: cannot decode as UTF-8")
            continue
        for line_number, line in enumerate(lines, start=1):
            if line.startswith(CONFLICT_MARKERS):
                errors.append(f"{rel_path}:{line_number}: leftover merge-conflict marker")
    return errors


def check_tracked_path_policy(paths: list[str]) -> list[str]:
    errors: list[str] = []
    for rel_path in paths:
        normalized = rel_path.replace("\\", "/")
        for prefix in FORBIDDEN_TRACKED_PREFIXES:
            if normalized.startswith(prefix):
                errors.append(f"{rel_path}: forbidden tracked path for Sprint 5 demo hygiene")
    return errors


def check_compose_contract(compose_json: Path) -> list[str]:
    compose = json.loads(compose_json.read_text(encoding="utf-8-sig"))
    services = compose.get("services", {})
    errors: list[str] = []

    missing = sorted(REQUIRED_SERVICES - set(services))
    if missing:
        errors.append(f"missing required Compose services: {', '.join(missing)}")
        return errors

    api_depends = services["api"].get("depends_on", {})
    streamlit_depends = services["streamlit"].get("depends_on", {})
    for name in ("postgres", "chromadb", "ollama"):
        if name not in api_depends:
            errors.append(f"api service must depend on {name}")
    if "api" not in streamlit_depends:
        errors.append("streamlit service must depend on api")

    if services["api"].get("healthcheck") is None:
        errors.append("api service must define a healthcheck")
    if services["streamlit"].get("healthcheck") is None:
        errors.append("streamlit service must define a healthcheck")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 5 integration gate for EduRAG demo readiness.")
    parser.add_argument(
        "--compose-json",
        type=Path,
        help="Optional docker compose config --format json output to validate.",
    )
    args = parser.parse_args()

    tracked_paths = _run_git_ls_files()
    errors = []
    errors.extend(check_no_conflict_markers(tracked_paths))
    errors.extend(check_tracked_path_policy(tracked_paths))

    if args.compose_json:
        errors.extend(check_compose_contract(args.compose_json))

    if errors:
        print("Sprint 5 integration gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Sprint 5 integration gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
