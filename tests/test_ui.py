import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from wireframe_studio.engines.base import Engine
from wireframe_studio.engines.registry import build_engines
from wireframe_studio.settings import Settings
from wireframe_studio.ui.main_window import MainWindow


class FakeEngine(Engine):
    def __init__(self, engine_id):
        self.id = engine_id
        self.name = engine_id.title()

    def run(self, rgb, variation=0, prompt=""):
        out = np.full(rgb.shape[:2], 255, np.uint8)
        out[10 + variation, :] = 0
        return out


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    engines = build_engines(tmp_path, Settings)  # no model files -> offline models unavailable
    for engine_id in ("lineart_realistic", "lineart_coarse", "lineart_anime", "dexined"):
        engines[engine_id] = FakeEngine(engine_id)
    settings = Settings(engine_id="lineart_realistic")
    win = MainWindow(settings, tmp_path / "settings.json", engines)
    yield win
    win.runner.wait()
    win.close()


def _wait(app, win):
    win.runner.wait()
    for _ in range(5):
        app.processEvents()


def _add_images(win, tmp_path, count=2):
    paths = []
    for i in range(count):
        path = tmp_path / f"img{i}.png"
        Image.new("RGB", (60, 40), (200, 50 + i, 50)).save(path)
        paths.append(path)
    win.add_files(paths)


def test_three_steps_produce_separate_outputs(app, window, tmp_path):
    _add_images(window, tmp_path)
    window.run_wireframe(window._targets())
    _wait(app, window)
    window.run_remove_bg(window._targets())
    _wait(app, window)
    window.run_vector(window._targets())
    _wait(app, window)
    for w in window.widgets:
        assert len(w.card.versions) == 1
        assert w.card.nobg is not None and w.card.svg.startswith("<svg")
        assert not w.busy and "⚠" not in w.status.text()
    out = tmp_path / "out"
    for w in window.widgets:
        w.card.save(out, window.weight, window.threshold)
    assert sorted(p.name for p in out.iterdir()) == [
        "img0.svg", "img0_nobg.png", "img0_wireframe.png", "img1.svg", "img1_nobg.png", "img1_wireframe.png",
    ]


def test_recreate_adds_version_with_next_variation(app, window, tmp_path):
    _add_images(window, tmp_path, 1)
    widget = window.widgets[0]
    window.run_wireframe([widget])
    _wait(app, window)
    widget.recreate_clicked.emit()
    _wait(app, window)
    assert [v.variation for v in widget.card.versions] == [0, 1]
    assert widget.version_label.text() == "2/2"
    window._step_version(widget, -1)
    assert widget.version_label.text() == "1/2"


def test_four_options_shows_grid_then_pick(app, window, tmp_path):
    _add_images(window, tmp_path, 1)
    window.four_check.setChecked(True)
    widget = window.widgets[0]
    window.run_wireframe([widget])
    _wait(app, window)
    assert len(widget.card.versions) == 4 and widget.card.choice == [0, 1, 2, 3]
    assert widget.result_stack.currentIndex() == 1
    window.run_remove_bg([widget])
    assert "Pick one" in widget.status.text()
    widget.choice_picked.emit(2)
    assert widget.card.selected == 2 and widget.result_stack.currentIndex() == 0


def test_checked_cards_limit_targets(app, window, tmp_path):
    _add_images(window, tmp_path, 3)
    window.widgets[1].checkbox.setChecked(True)
    assert window._targets() == [window.widgets[1]]


def test_gemini_without_key_shows_error_on_card(app, window, tmp_path):
    _add_images(window, tmp_path, 1)
    window.engine_combo.setCurrentIndex(window.engine_combo.findData("gemini"))
    widget = window.widgets[0]
    assert not widget.prompt_row.isHidden()
    window.run_wireframe([widget])
    _wait(app, window)
    assert "API key" in widget.status.text() and not widget.busy


def test_threshold_change_updates_cutout_and_drops_svg(app, window, tmp_path):
    _add_images(window, tmp_path, 1)
    widget = window.widgets[0]
    for step in (window.run_wireframe, window.run_vector):
        step([widget])
        _wait(app, window)
    assert widget.card.svg is not None
    window.threshold_slider.setValue(120)
    assert widget.card.svg is None and widget.card.nobg is not None


def test_unsupported_and_missing_offline_models_are_disabled(app, tmp_path):
    win = MainWindow(Settings(), tmp_path / "s.json", build_engines(tmp_path, Settings))
    model = win.engine_combo.model()
    enabled = {win.engine_combo.itemData(i): model.item(i).isEnabled() for i in range(win.engine_combo.count())}
    assert enabled["classic"] and enabled["gemini"] and not enabled["dexined"]
    assert win.engine_combo.currentData() == "classic"
    win.close()
