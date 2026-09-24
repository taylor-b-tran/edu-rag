"""One confidence scale, shared by the pipeline and the page.

The pipeline labelled a 0.64 answer "High" (its threshold was 0.60) while the page coloured the
bar from its own 0.80 / 0.50 thresholds and painted it gold. These tests pin the two together by
behaviour, not only by constant.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

APP = Path(__file__).resolve().parents[1] / "apps" / "streamlit"
sys.path.insert(0, str(APP))
import main  # noqa: E402

from src.document_processor import rag_pipeline  # noqa: E402

GREEN, GOLD, RED = "#10B981", "#D4A843", "#EF4444"


def _pipeline_band(score: float) -> str:
    label, _ = rag_pipeline.LLMResponseGeneration._confidence([SimpleNamespace(similarity=score)])
    return label


def test_page_thresholds_equal_the_pipeline_thresholds():
    assert main._CONFIDENCE_HIGH == rag_pipeline.CONFIDENCE_HIGH
    assert main._CONFIDENCE_MEDIUM == rag_pipeline.CONFIDENCE_MEDIUM


def test_every_score_lands_in_the_same_band_on_both_sides():
    for step in range(1, 100):
        score = step / 100
        assert main._confidence_band(None, score) == _pipeline_band(score), score


def test_the_answer_from_the_workshop_is_high_in_both_label_and_colour():
    # 22 Sep capture: the API returned confidence "High" with confidence_score 0.64.
    band = main._confidence_band("High", 0.64)
    assert band == "High"
    assert main._BAND_COLOURS[band] == GREEN
    assert main.get_confidence_label("High") == "High confidence"


def test_the_band_the_pipeline_returned_wins_over_the_score():
    assert main._confidence_band("Medium", 0.95) == "Medium"
    assert main._confidence_band("low", 0.95) == "Low"


@pytest.mark.parametrize("score, band", [
    (0.60, "High"), (0.599, "Medium"),
    (0.35, "Medium"), (0.349, "Low"),
    (0.01, "Low"), (0.0, None),
])
def test_boundaries(score, band):
    assert main._confidence_band(None, score) == band


def test_band_colours():
    assert main._BAND_COLOURS == {"High": GREEN, "Medium": GOLD, "Low": RED}


def test_no_confidence_at_all():
    assert main._confidence_band(None, None) is None
    assert main.get_confidence_label(None) == "No confidence data"


@pytest.mark.parametrize("label", ["high", "medium", "low"])
def test_a_bar_drawn_from_a_label_alone_sits_inside_its_band(label):
    width = main._confidence_score(label)
    assert main._confidence_band(None, width) == label.capitalize()


def test_pipeline_bands():
    assert _pipeline_band(0.64) == "High"
    assert _pipeline_band(0.50) == "Medium"
    assert _pipeline_band(0.20) == "Low"
    assert rag_pipeline.LLMResponseGeneration._confidence([]) == ("Low", 0.0)
