"""The default model has to be the same model everywhere it is written down.

Four files name it, and they drifted apart before: docker-compose fell back to
llama3.2 for the pipeline and qwen3:14b for warmup, so a stack started without a
.env loaded one model into VRAM and then asked Ollama for another on every
query. start_stack.ps1 is the sharper trap -- it rewrites DEFAULT_OLLAMA_MODEL
in .env from detected VRAM, so a high-tier value that disagrees with the compose
default silently undoes a deliberate change the next time anyone runs it.
"""
from __future__ import annotations

import os
import re

import pytest

from src.api.routes.settings import KNOWN_MODELS

REPO = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    with open(os.path.join(REPO, *parts), "r", encoding="utf-8") as f:
        return f.read()


def _compose_defaults():
    return re.findall(r"\$\{DEFAULT_OLLAMA_MODEL:-([^}]+)\}", _read("docker-compose.yml"))


def test_every_compose_fallback_names_the_same_model():
    defaults = _compose_defaults()
    assert defaults, "no DEFAULT_OLLAMA_MODEL fallback found in docker-compose.yml"
    assert len(set(defaults)) == 1, f"compose fallbacks disagree: {sorted(set(defaults))}"


def test_the_start_script_high_tier_matches_the_compose_default():
    script = _read("scripts", "start_stack.ps1")
    high = re.search(r"\$HighVramModel\s*=\s*\"([^\"]+)\"", script)
    assert high, "could not find $HighVramModel in start_stack.ps1"
    assert high.group(1) == _compose_defaults()[0]


def test_env_example_matches_the_compose_default():
    example = re.search(r"^DEFAULT_OLLAMA_MODEL=(.+)$", _read(".env.example"), re.MULTILINE)
    assert example, "no DEFAULT_OLLAMA_MODEL line in .env.example"
    assert example.group(1).strip() == _compose_defaults()[0]


def test_the_default_model_is_one_the_admin_screen_offers():
    names = [m["name"] for m in KNOWN_MODELS]
    assert _compose_defaults()[0] in names


@pytest.mark.parametrize("entry", KNOWN_MODELS, ids=lambda e: e["name"])
def test_every_offered_model_explains_itself(entry):
    # The picker shows the note under the choice; an entry without one is a
    # blank line on the admin screen.
    assert entry["name"].strip()
    assert entry.get("note", "").strip()
    assert isinstance(entry.get("vram_gb"), int)
