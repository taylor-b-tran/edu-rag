"""The admin model control.

It was a free-text box defaulted to a hard-coded "qwen3:14b", so the one
setting that decides what sits in 16 GB of shared VRAM was typed from memory
and silently showed the wrong default once the real default moved. It is now a
list of the models measured against this corpus -- without becoming a
whitelist, because an admin who has just pulled something new must still be
able to select it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "streamlit"))


CATALOGUE = [
    {"name": "gemma4:12b", "vram_gb": 11, "note": "Default."},
    {"name": "qwen3.5:9b", "vram_gb": 6, "note": "Faster, wordier."},
]


class _FakeSt:
    """Records what the widgets were offered and answers as a user would."""
    def __init__(self, picks=None, typed=""):
        self.options, self.index, self.captions = None, None, []
        self.used_text_input = False
        self._picks, self._typed = picks, typed

    def selectbox(self, label, options, index=0, **kw):
        self.options, self.index = list(options), index
        return self._picks if self._picks is not None else self.options[index]

    def text_input(self, label, value="", **kw):
        self.used_text_input = True
        return self._typed or value

    def caption(self, text, *a, **kw):
        self.captions.append(text)


@pytest.fixture
def ui(monkeypatch):
    import main
    return main, monkeypatch


def test_nothing_stored_offers_the_catalogue_and_lands_on_the_default(ui):
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker(None, CATALOGUE, disabled=False)

    assert chosen == "gemma4:12b"
    assert fake.options[:2] == ["gemma4:12b", "qwen3.5:9b"]
    assert fake.options[-1] == main._OTHER_MODEL
    assert fake.captions == ["Default."]


def test_a_model_the_catalogue_does_not_list_is_kept_and_preselected(ui):
    """The API accepts any name. If the screen dropped one it did not
    recognise, opening the page and saving would change the model by accident."""
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker("mistral-small:24b", CATALOGUE, disabled=False)

    assert chosen == "mistral-small:24b"
    assert fake.options[fake.index] == "mistral-small:24b"


def test_choosing_other_returns_what_was_typed(ui):
    main, monkeypatch = ui
    fake = _FakeSt(picks=None, typed="  phi4:14b  ")
    monkeypatch.setattr(main, "st", fake)
    fake._picks = main._OTHER_MODEL

    assert main._model_picker(None, CATALOGUE, disabled=False) == "phi4:14b"
    assert fake.used_text_input


def test_no_catalogue_falls_back_to_a_plain_box(ui):
    """Fixture mode, or the API is down: the screen still has to render and
    must not lose the value already in effect."""
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    assert main._model_picker("qwen3:14b", [], disabled=True) == "qwen3:14b"
    assert fake.used_text_input
    assert fake.options is None


def test_the_real_catalogue_drives_the_picker(ui):
    """Guards the contract between the API payload and this widget."""
    from src.api.routes.settings import KNOWN_MODELS
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker(None, KNOWN_MODELS, disabled=False)
    assert chosen == KNOWN_MODELS[0]["name"]
    assert len(fake.options) == len(KNOWN_MODELS) + 1


def test_with_nothing_stored_the_picker_shows_what_is_actually_in_effect(ui):
    """It used to land on the first catalogue entry, which is only right on a
    host that happens to run it. On a smaller machine the screen told the
    admin it was serving a model it was not."""
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker(None, CATALOGUE, disabled=False, effective="qwen3.5:9b")
    assert chosen == "qwen3.5:9b"


def test_an_effective_model_outside_the_catalogue_is_still_shown(ui):
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker(None, CATALOGUE, disabled=False, effective="llama3.2")
    assert chosen == "llama3.2"
    assert "llama3.2" in fake.options


def test_a_stored_override_still_wins_over_the_effective_default(ui):
    main, monkeypatch = ui
    fake = _FakeSt()
    monkeypatch.setattr(main, "st", fake)

    chosen = main._model_picker("gemma4:12b", CATALOGUE, disabled=False, effective="llama3.2")
    assert chosen == "gemma4:12b"
