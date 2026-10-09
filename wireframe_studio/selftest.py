"""Headless check that the packaged app works: engines, steps 2/3, and the Qt window.

Exit code 0 = OK. Used by CI on the built WireframeStudio.exe.
"""
import tempfile
import time
import traceback
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np

from .core.cleanup import remove_background
from .core.lineweight import apply_line_weight
from .core.vectorize import trace_to_svg
from .engines.registry import build_engines
from .paths import models_dir
from .settings import Settings


def synthetic_image() -> np.ndarray:
    rgb = np.full((360, 480, 3), (235, 240, 245), np.uint8)
    cv2.rectangle(rgb, (60, 80), (300, 280), (40, 90, 160), -1)
    cv2.circle(rgb, (360, 180), 70, (200, 60, 50), -1)
    cv2.line(rgb, (40, 320), (440, 300), (20, 20, 20), 6)
    return rgb


def run(require_models: bool, log) -> int:
    failures = 0
    rgb = synthetic_image()
    engines = build_engines(models_dir(), Settings)
    for engine in engines.values():
        if engine.online:
            continue
        if not engine.available():
            log(f"{'FAIL' if require_models else 'skip'} {engine.id}: {engine.unavailable_reason()}")
            failures += require_models
            continue
        try:
            start = time.time()
            out = engine.run(rgb)
            assert out.shape == rgb.shape[:2] and out.dtype == np.uint8, out.shape
            assert out.mean() > 128, "expected mostly white background"
            rgba = remove_background(apply_line_weight(out, 2), 200)
            assert set(np.unique(rgba[..., 3])) <= {0, 255}
            assert (rgba[..., 3] == 255).any(), "no lines found"
            log(f"ok   {engine.id} ({time.time() - start:.1f}s)")
        except Exception:
            failures += 1
            log(f"FAIL {engine.id}\n{traceback.format_exc()}")
    try:
        gray = engines["classic"].run(rgb)
        svg = trace_to_svg(remove_background(apply_line_weight(gray, 2), 200))
        assert len(ET.fromstring(svg).findall("{http://www.w3.org/2000/svg}path")) == 1
        log("ok   vectorize")
    except Exception:
        failures += 1
        log(f"FAIL vectorize\n{traceback.format_exc()}")
    try:
        from PySide6.QtWidgets import QApplication

        from .ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(Settings(), Path(tmp) / "settings.json", engines)
            window.close()
            app.processEvents()
        log("ok   ui")
    except Exception:
        failures += 1
        log(f"FAIL ui\n{traceback.format_exc()}")
    log("SELF-TEST PASSED" if not failures else f"SELF-TEST FAILED ({failures})")
    return 1 if failures else 0
