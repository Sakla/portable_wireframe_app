"""Settings and large-preview dialogs."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout,
)

from ..settings import DEFAULT_PROMPT, GEMINI_MODELS, Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 380)
        self.settings = settings

        self.key_edit = QLineEdit(settings.gemini_api_key)
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Paste the key from aistudio.google.com")
        show_key = QCheckBox("Show")
        show_key.toggled.connect(
            lambda on: self.key_edit.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
        )
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(GEMINI_MODELS)
        self.model_combo.setCurrentText(settings.gemini_model)
        self.prompt_edit = QPlainTextEdit(settings.default_prompt)
        reset = QPushButton("Reset prompt to default")
        reset.clicked.connect(lambda: self.prompt_edit.setPlainText(DEFAULT_PROMPT))

        form = QFormLayout()
        form.addRow("Gemini API key:", self.key_edit)
        form.addRow("", show_key)
        form.addRow("Gemini model:", self.model_combo)
        form.addRow("Default prompt\n(for new images):", self.prompt_edit)
        form.addRow("", reset)
        note = QLabel("Settings, including the API key, are saved in plain text in settings.json "
                      "next to WireframeStudio.exe.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #666;")
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def apply(self):
        self.settings.gemini_api_key = self.key_edit.text().strip()
        self.settings.gemini_model = self.model_combo.currentText().strip() or GEMINI_MODELS[0]
        self.settings.default_prompt = self.prompt_edit.toPlainText().strip() or DEFAULT_PROMPT


class PreviewDialog(QDialog):
    def __init__(self, title: str, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        label = QLabel(alignment=Qt.AlignCenter)
        label.setPixmap(pixmap)
        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        self.resize(min(pixmap.width() + 40, 1400), min(pixmap.height() + 40, 950))
