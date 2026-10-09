"""One image card: original, current result, versions, Recreate, Save, Gemini prompt."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QSizePolicy, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from ..model.card import Card
from .qimage import svg_thumbnail, thumbnail

THUMB = 260
GRID_THUMB = 126


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class CardWidget(QFrame):
    recreate_clicked = Signal()
    save_clicked = Signal()
    remove_clicked = Signal()
    version_step = Signal(int)
    choice_picked = Signal(int)
    preview_requested = Signal()

    def __init__(self, card: Card, parent=None):
        super().__init__(parent)
        self.card = card
        self.busy = False
        self.setObjectName("card")
        self.setFrameShape(QFrame.StyledPanel)

        self.checkbox = QCheckBox(card.name)
        self.checkbox.setToolTip("Tick cards to run the step buttons only on them (none ticked = all)")
        self.status = QLabel()
        self.status.setWordWrap(True)
        remove = QToolButton(text="✕")
        remove.setToolTip("Remove this image from the list")
        remove.clicked.connect(self.remove_clicked)
        header = QHBoxLayout()
        header.addWidget(self.checkbox)
        header.addWidget(self.status, 1)
        header.addWidget(remove)

        self.original_label = QLabel(alignment=Qt.AlignCenter)
        self.original_label.setFixedSize(THUMB, THUMB)
        self.original_label.setPixmap(thumbnail(card.original, THUMB))
        arrow = QLabel("→", alignment=Qt.AlignCenter)
        arrow.setStyleSheet("font-size: 22px; color: #888;")

        self.result_label = ClickableLabel("No result yet.\nClick “1. Wireframe”.")
        self.result_label.setFixedSize(THUMB, THUMB)
        self.result_label.setToolTip("Click to view larger")
        self.result_label.clicked.connect(self.preview_requested)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(4)
        self.result_stack = QStackedWidget()
        self.result_stack.addWidget(self.result_label)
        self.result_stack.addWidget(self.grid_host)
        self.result_stack.setFixedSize(THUMB, THUMB + 24)
        self.stage_label = QLabel(alignment=Qt.AlignCenter)
        self.stage_label.setStyleSheet("color: #666;")
        result_col = QVBoxLayout()
        result_col.addWidget(self.result_stack)
        result_col.addWidget(self.stage_label)

        self.prev_button = QToolButton(text="◀")
        self.next_button = QToolButton(text="▶")
        self.prev_button.clicked.connect(lambda: self.version_step.emit(-1))
        self.next_button.clicked.connect(lambda: self.version_step.emit(1))
        self.version_label = QLabel("0/0", alignment=Qt.AlignCenter)
        self.version_label.setMinimumWidth(48)
        self.recreate_button = QPushButton("⟳ Recreate")
        self.recreate_button.setToolTip("Make a new wireframe version with the current engine")
        self.recreate_button.clicked.connect(self.recreate_clicked)
        self.save_button = QPushButton("Save")
        self.save_button.setToolTip("Save wireframe PNG, background-free PNG and SVG (whatever exists)")
        self.save_button.clicked.connect(self.save_clicked)
        versions = QHBoxLayout()
        versions.addWidget(self.prev_button)
        versions.addWidget(self.version_label)
        versions.addWidget(self.next_button)
        controls = QVBoxLayout()
        controls.addStretch(1)
        controls.addLayout(versions)
        controls.addWidget(self.recreate_button)
        controls.addWidget(self.save_button)
        controls.addStretch(1)

        body = QHBoxLayout()
        body.addWidget(self.original_label)
        body.addWidget(arrow)
        body.addLayout(result_col)
        body.addSpacing(12)
        body.addLayout(controls)
        body.addStretch(1)

        self.prompt_edit = QPlainTextEdit(card.prompt)
        self.prompt_edit.setPlaceholderText("Gemini prompt for this image")
        self.prompt_edit.setFixedHeight(64)
        self.prompt_edit.textChanged.connect(self._prompt_changed)
        self.prompt_row = QWidget()
        prompt_layout = QHBoxLayout(self.prompt_row)
        prompt_layout.setContentsMargins(0, 0, 0, 0)
        prompt_layout.addWidget(QLabel("Gemini prompt:"))
        prompt_layout.addWidget(self.prompt_edit, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addLayout(body)
        layout.addWidget(self.prompt_row)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def _prompt_changed(self):
        self.card.prompt = self.prompt_edit.toPlainText()

    def set_busy(self, busy: bool, message: str = "Working…"):
        self.busy = busy
        self.recreate_button.setEnabled(not busy)
        if busy:
            self.status.setStyleSheet("color: #1a5fb4;")
            self.status.setText(f"⏳ {message}")
        else:
            self.status.clear()

    def set_error(self, message: str):
        self.busy = False
        self.recreate_button.setEnabled(True)
        self.status.setStyleSheet("color: #c01c28;")
        self.status.setText(f"⚠ {message}")

    def refresh(self, weight, threshold, show_prompt: bool):
        card = self.card
        self.prompt_row.setVisible(show_prompt)
        count = len(card.versions)
        self.version_label.setText(f"{card.selected + 1}/{count}" if count else "0/0")
        self.prev_button.setEnabled(count > 1 and card.selected > 0)
        self.next_button.setEnabled(count > 1 and card.selected < count - 1)

        if card.choice:
            self._show_choice_grid(weight, threshold)
            self.stage_label.setText("Pick the option you like")
            return
        self.result_stack.setCurrentIndex(0)
        height, width = card.original.shape[:2]
        if card.svg is not None:
            self.result_label.setPixmap(svg_thumbnail(card.svg, width, height, THUMB))
            stage = "Vector (SVG)"
        elif card.nobg is not None:
            self.result_label.setPixmap(thumbnail(card.nobg, THUMB))
            stage = "Background removed"
        elif card.versions:
            self.result_label.setPixmap(thumbnail(card.wireframe(weight, threshold), THUMB))
            stage = "Wireframe"
        else:
            self.result_label.clear()
            self.result_label.setText("No result yet.\nClick “1. Wireframe”.")
            stage = ""
        version = card.current_version
        if version is not None:
            stage += f" · {version.engine_name}" + (f" #{version.variation + 1}" if version.variation else "")
        self.stage_label.setText(stage)

    def _show_choice_grid(self, weight, threshold):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        card = self.card
        for slot, index in enumerate(card.choice):
            version = card.versions[index]
            tile = ClickableLabel()
            tile.setPixmap(thumbnail(card.wireframe_of(index, weight, threshold), GRID_THUMB))
            tile.setToolTip(f"{version.engine_name} — click to choose")
            tile.setStyleSheet("border: 1px solid #bbb; background: white;")
            tile.setFixedSize(GRID_THUMB, GRID_THUMB)
            tile.clicked.connect(lambda i=index: self.choice_picked.emit(i))
            caption = QLabel(version.engine_name, alignment=Qt.AlignCenter)
            caption.setStyleSheet("font-size: 10px; color: #444;")
            cell = QVBoxLayout()
            cell.setSpacing(0)
            cell.addWidget(tile)
            cell.addWidget(caption)
            holder = QWidget()
            holder.setLayout(cell)
            self.grid.addWidget(holder, slot // 2, slot % 2)
        self.result_stack.setCurrentIndex(1)
