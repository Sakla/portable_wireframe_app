"""Main window: toolbar with the 3 step buttons and options, and a scrolling list of image cards."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from ..core.cleanup import remove_background
from ..core.imageio import SUPPORTED_EXTENSIONS, ImageLoadError, load_rgb
from ..core.vectorize import trace_to_svg
from ..engines.base import EngineError
from ..engines.registry import FOUR_OPTIONS
from ..model.card import Card, Version, unique_name
from ..settings import LINE_WEIGHTS, Settings
from .card_widget import CardWidget
from .dialogs import PreviewDialog, SettingsDialog
from .qimage import svg_thumbnail, thumbnail
from .workers import Runner

IMAGE_FILTER = "Images (" + " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS)) + ")"


def run_engines(engines, original, variations, prompt):
    """Run one or more engines; returns versions, raises EngineError only if all fail."""
    versions, errors = [], []
    for engine in engines:
        try:
            raw = engine.run(original, variation=variations[engine.id], prompt=prompt)
            versions.append(Version(raw, engine.id, engine.name, variations[engine.id]))
        except EngineError as exc:
            errors.append(str(exc))
    if not versions:
        raise EngineError(" | ".join(errors))
    return versions


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, settings_path: Path, engines: dict, runner: Runner | None = None):
        super().__init__()
        self.settings = settings
        self.settings_path = Path(settings_path)
        self.engines = engines
        self.runner = runner or Runner()
        self.widgets: list[CardWidget] = []
        self.setWindowTitle("Wireframe Studio")
        self.resize(1080, 820)
        self.setAcceptDrops(True)
        self._build_ui()
        self._refresh_engine_combo()

    # ---- layout -----------------------------------------------------------------
    def _build_ui(self):
        add = QPushButton("+ Add images")
        add.clicked.connect(self._choose_files)
        save_all = QPushButton("Save all")
        save_all.clicked.connect(self.save_all)
        settings_button = QPushButton("Settings…")
        settings_button.clicked.connect(self._open_settings)
        self.step1 = QPushButton("1. Wireframe")
        self.step2 = QPushButton("2. Remove BG")
        self.step3 = QPushButton("3. Vector")
        for button in (self.step1, self.step2, self.step3):
            button.setMinimumHeight(34)
            button.setStyleSheet("font-weight: bold; padding: 0 14px;")
        self.step1.clicked.connect(lambda: self.run_wireframe(self._targets()))
        self.step2.clicked.connect(lambda: self.run_remove_bg(self._targets()))
        self.step3.clicked.connect(lambda: self.run_vector(self._targets()))
        row1 = QHBoxLayout()
        for w in (add, save_all, settings_button):
            row1.addWidget(w)
        row1.addStretch(1)
        for w in (self.step1, self.step2, self.step3):
            row1.addWidget(w)

        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(220)
        self.engine_combo.currentIndexChanged.connect(self._engine_changed)
        self.weight_combo = QComboBox()
        for weight in LINE_WEIGHTS:
            self.weight_combo.addItem("Natural" if weight is None else f"{weight} px", weight)
        self.weight_combo.setCurrentIndex(max(0, LINE_WEIGHTS.index(self.settings.line_weight))
                                          if self.settings.line_weight in LINE_WEIGHTS else 0)
        self.weight_combo.setToolTip("Natural keeps the engine's own lines; px values make every line that thick")
        self.weight_combo.currentIndexChanged.connect(self._look_changed)
        self.four_check = QCheckBox("Show 4 options")
        self.four_check.setToolTip("Compare 4 offline engines side by side and click the one you like")
        self.four_check.setChecked(self.settings.four_options)
        self.four_check.toggled.connect(self._four_toggled)
        self.threshold_slider = QSlider(Qt.Horizontal, minimum=50, maximum=254, value=self.settings.threshold)
        self.threshold_slider.setTracking(False)
        self.threshold_slider.setFixedWidth(130)
        self.threshold_slider.setToolTip("Pixels darker than this become solid black; lighter ones transparent")
        self.threshold_value = QLabel(str(self.settings.threshold))
        self.threshold_slider.sliderMoved.connect(lambda v: self.threshold_value.setText(str(v)))
        self.threshold_slider.valueChanged.connect(self._look_changed)
        self.smooth_slider = QSlider(Qt.Horizontal, minimum=0, maximum=13,
                                     value=round(self.settings.smoothness * 10))
        self.smooth_slider.setFixedWidth(100)
        self.smooth_slider.setToolTip("Vector curve smoothness: left = sharp corners, right = round")
        self.smooth_slider.valueChanged.connect(self._smoothness_changed)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Engine:"))
        row2.addWidget(self.engine_combo)
        row2.addSpacing(10)
        row2.addWidget(QLabel("Line weight:"))
        row2.addWidget(self.weight_combo)
        row2.addSpacing(10)
        row2.addWidget(self.four_check)
        row2.addSpacing(10)
        row2.addWidget(QLabel("Black threshold:"))
        row2.addWidget(self.threshold_slider)
        row2.addWidget(self.threshold_value)
        row2.addSpacing(10)
        row2.addWidget(QLabel("Smoothness:"))
        row2.addWidget(self.smooth_slider)
        row2.addStretch(1)

        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.empty_label = QLabel("Drop images here, or click “+ Add images”.\n\n"
                                  "1. Wireframe → 2. Remove BG → 3. Vector", alignment=Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #888; font-size: 16px; padding: 80px;")
        self.cards_layout.addWidget(self.empty_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cards_host)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(scroll, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    def _refresh_engine_combo(self):
        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        model: QStandardItemModel = self.engine_combo.model()
        for engine in self.engines.values():
            label = engine.name
            if not engine.available():
                label += f"  ({engine.unavailable_reason()})"
            self.engine_combo.addItem(label, engine.id)
            if not engine.available() and not engine.online:
                model.item(self.engine_combo.count() - 1).setEnabled(False)
        index = self.engine_combo.findData(self.settings.engine_id)
        if index < 0 or not model.item(index).isEnabled():
            index = next((i for i in range(self.engine_combo.count()) if model.item(i).isEnabled()), 0)
        self.engine_combo.setCurrentIndex(index)
        self.settings.engine_id = self.engine_combo.currentData()
        self.engine_combo.blockSignals(False)

    # ---- settings changes -------------------------------------------------------
    @property
    def weight(self):
        return self.weight_combo.currentData()

    @property
    def threshold(self):
        return self.threshold_slider.value()

    def _save_settings(self):
        try:
            self.settings.save(self.settings_path)
        except OSError as exc:
            self.statusBar().showMessage(f"Could not save settings: {exc}")

    def _engine_changed(self):
        self.settings.engine_id = self.engine_combo.currentData()
        self._save_settings()
        self._refresh_all()

    def _four_toggled(self, on):
        self.settings.four_options = on
        self._save_settings()

    def _smoothness_changed(self, value):
        self.settings.smoothness = value / 10
        self._save_settings()

    def _look_changed(self):
        """Line weight or threshold changed: update cut-outs live, vectors need re-running."""
        self.settings.line_weight = self.weight
        self.settings.threshold = self.threshold
        self.threshold_value.setText(str(self.threshold))
        self._save_settings()
        for w in self.widgets:
            if not w.busy and w.card.nobg is not None:
                w.card.nobg = remove_background(w.card.wireframe(self.weight, self.threshold), self.threshold)
                w.card.svg = None
        self._refresh_all()

    def _open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            dialog.apply()
            self._save_settings()
            self._refresh_engine_combo()
            self._refresh_all()

    # ---- cards ------------------------------------------------------------------
    def _choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add images", self.settings.last_dir, IMAGE_FILTER)
        if paths:
            self.settings.last_dir = str(Path(paths[0]).parent)
            self._save_settings()
            self.add_files(paths)

    def add_files(self, paths):
        errors = []
        taken = {w.card.name for w in self.widgets}
        for path in map(Path, paths):
            if path.is_dir():
                self.add_files(sorted(p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS))
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                errors.append(f"{path.name}: unsupported file type")
                continue
            try:
                rgb = load_rgb(path)
            except ImageLoadError as exc:
                errors.append(str(exc))
                continue
            name = unique_name(path.stem, taken)
            taken.add(name)
            self._add_card(Card(name=name, original=rgb, prompt=self.settings.default_prompt))
        if errors:
            QMessageBox.warning(self, "Some files were skipped", "\n".join(errors))

    def _add_card(self, card: Card) -> CardWidget:
        widget = CardWidget(card)
        widget.recreate_clicked.connect(lambda: self.run_wireframe([widget]))
        widget.save_clicked.connect(lambda: self.save_cards([widget]))
        widget.remove_clicked.connect(lambda: self._remove(widget))
        widget.version_step.connect(lambda d: self._step_version(widget, d))
        widget.choice_picked.connect(lambda i: self._pick(widget, i))
        widget.preview_requested.connect(lambda: self._preview(widget))
        self.widgets.append(widget)
        self.cards_layout.addWidget(widget)
        self.empty_label.hide()
        self._refresh(widget)
        return widget

    def _remove(self, widget):
        if widget.busy:
            return
        self.widgets.remove(widget)
        widget.deleteLater()
        self.empty_label.setVisible(not self.widgets)

    def _targets(self):
        checked = [w for w in self.widgets if w.checkbox.isChecked()]
        return checked or list(self.widgets)

    def _refresh(self, widget):
        widget.refresh(self.weight, self.threshold, show_prompt=self.settings.engine_id == "gemini")

    def _refresh_all(self):
        for widget in self.widgets:
            self._refresh(widget)

    def _step_version(self, widget, delta):
        card = widget.card
        if widget.busy or not card.versions:
            return
        card.choice = []
        card.select(max(0, min(len(card.versions) - 1, card.selected + delta)))
        self._refresh(widget)

    def _pick(self, widget, index):
        widget.card.pick_choice(index)
        self._refresh(widget)

    def _preview(self, widget):
        card = widget.card
        height, width = card.original.shape[:2]
        if card.svg is not None:
            pixmap = svg_thumbnail(card.svg, width, height, max(width, height))
        elif card.nobg is not None:
            pixmap = thumbnail(card.nobg, max(width, height))
        elif card.versions:
            pixmap = thumbnail(card.wireframe(self.weight, self.threshold), max(width, height))
        else:
            return
        PreviewDialog(card.name, pixmap, self).exec()

    # ---- the three steps ----------------------------------------------------------
    def _start(self, widgets, message, make_job, apply_result):
        started = 0
        for widget in widgets:
            if widget.busy:
                continue
            job = make_job(widget)
            if job is None:
                continue
            widget.set_busy(True, message)
            started += 1

            def done(result, w=widget):
                apply_result(w, result)
                w.set_busy(False)
                self._refresh(w)
                self._update_status()

            def failed(error, w=widget):
                w.set_error(error)
                self._update_status()

            self.runner.submit(job, done, failed)
        self._update_status()
        return started

    def _update_status(self):
        busy = sum(w.busy for w in self.widgets)
        self.statusBar().showMessage(f"Working on {busy} image(s)…" if busy else "Ready")

    def run_wireframe(self, widgets):
        if self.settings.four_options:
            engines = [self.engines[e] for e in FOUR_OPTIONS if self.engines[e].available()]
            as_choice = len(engines) > 1
            if not engines:
                for w in widgets:
                    w.set_error("No offline models found in the models folder.")
                return
        else:
            engines = [self.engines[self.settings.engine_id]]
            as_choice = False

        def make_job(widget):
            card = widget.card
            variations = {e.id: card.next_variation(e.id) for e in engines}
            original, prompt = card.original, card.prompt
            return lambda: run_engines(engines, original, variations, prompt)

        def apply(widget, versions):
            widget.card.add_versions(versions, as_choice=as_choice and len(versions) > 1)

        label = "Comparing 4 engines…" if as_choice else f"Making wireframe ({engines[0].name})…"
        self._start(widgets, label, make_job, apply)

    def run_remove_bg(self, widgets):
        weight, threshold = self.weight, self.threshold

        def make_job(widget):
            card = widget.card
            if card.choice:
                widget.set_error("Pick one of the 4 options first.")
                return None
            return lambda: remove_background(card.wireframe(weight, threshold), threshold)

        def apply(widget, rgba):
            widget.card.nobg, widget.card.svg = rgba, None

        self._start(widgets, "Removing background…", make_job, apply)

    def run_vector(self, widgets):
        weight, threshold, smoothness = self.weight, self.threshold, self.settings.smoothness

        def make_job(widget):
            card = widget.card
            if card.choice:
                widget.set_error("Pick one of the 4 options first.")
                return None
            nobg = card.nobg

            def job():
                rgba = nobg if nobg is not None else remove_background(card.wireframe(weight, threshold), threshold)
                return rgba, trace_to_svg(rgba, smoothness=smoothness)
            return job

        def apply(widget, result):
            widget.card.nobg, widget.card.svg = result

        self._start(widgets, "Tracing vector…", make_job, apply)

    # ---- saving -------------------------------------------------------------------
    def save_all(self):
        self.save_cards(list(self.widgets))

    def save_cards(self, widgets):
        if not widgets:
            return
        folder = QFileDialog.getExistingDirectory(self, "Save to folder", self.settings.last_dir)
        if not folder:
            return
        self.settings.last_dir = folder
        self._save_settings()
        written = []
        try:
            for widget in widgets:
                written += widget.card.save(Path(folder), self.weight, self.threshold)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        if not written:
            self.statusBar().showMessage("Nothing to save yet — run a step first.")
        else:
            self.statusBar().showMessage(f"Saved {len(written)} file(s) to {folder}")

    # ---- drag and drop ----------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.add_files(paths)
            event.acceptProposedAction()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)
