import numpy as np
import pytest
from PIL import Image

from wireframe_studio.model.card import Card, Version, unique_name


def _card():
    rgb = np.full((20, 30, 3), 255, np.uint8)
    rgb[10, :] = 0
    return Card(name="chair", original=rgb)


def _version(engine="e", value=255):
    raw = np.full((20, 30), value, np.uint8)
    raw[5, :] = 0
    return Version(raw=raw, engine_id=engine, engine_name=engine.upper(), variation=0)


def test_adding_versions_selects_newest():
    card = _card()
    card.add_versions([_version(), _version()])
    assert card.selected == 1 and card.choice == []


def test_four_options_selects_first_and_remembers_choice():
    card = _card()
    card.add_versions([_version()])
    card.add_versions([_version(), _version(), _version(), _version()], as_choice=True)
    assert card.selected == 1 and card.choice == [1, 2, 3, 4]
    card.pick_choice(3)
    assert card.selected == 3 and card.choice == []


def test_selecting_other_version_clears_outputs():
    card = _card()
    card.add_versions([_version(), _version()])
    card.nobg, card.svg = np.zeros((20, 30, 4), np.uint8), "<svg/>"
    card.select(0)
    assert card.nobg is None and card.svg is None


def test_select_out_of_range():
    with pytest.raises(IndexError):
        _card().select(0)


def test_next_variation_counts_same_engine_runs():
    card = _card()
    card.add_versions([_version("a"), _version("b"), _version("a")])
    assert card.next_variation("a") == 2 and card.next_variation("c") == 0


def test_wireframe_uses_original_when_no_versions():
    wf = _card().wireframe(None, 200)
    assert wf[10, 0] == 0 and wf[0, 0] == 255


def test_wireframe_applies_line_weight_to_selected_version():
    card = _card()
    card.add_versions([_version()])
    assert (card.wireframe(3, 200)[:, 15] < 128).sum() == 3


def test_save_writes_existing_stages(tmp_path):
    card = _card()
    assert card.save(tmp_path, None, 200) == []
    card.add_versions([_version()])
    card.nobg = np.zeros((20, 30, 4), np.uint8)
    card.svg = "<svg/>"
    names = sorted(p.name for p in card.save(tmp_path, None, 200))
    assert names == ["chair.svg", "chair_nobg.png", "chair_wireframe.png"]
    assert Image.open(tmp_path / "chair_nobg.png").mode == "RGBA"


def test_unique_name():
    assert unique_name("a", set()) == "a"
    assert unique_name("a", {"a", "a (2)"}) == "a (3)"
