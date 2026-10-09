"""All wireframe engines, in dropdown order."""
from pathlib import Path
from typing import Callable

from ..settings import Settings
from .base import Engine
from .classic import ClassicEngine
from .dexined import DexinedEngine
from .gemini import GeminiEngine
from .lineart import LineartEngine

MODEL_FILES = {
    "lineart_realistic": "lineart.onnx",
    "lineart_coarse": "lineart_coarse.onnx",
    "lineart_anime": "lineart_anime.onnx",
    "dexined": "dexined.onnx",
}

# Engines compared side by side by "Show 4 options".
FOUR_OPTIONS = ["lineart_realistic", "lineart_coarse", "lineart_anime", "dexined"]


def build_engines(models_dir: Path, settings_provider: Callable[[], Settings]) -> dict[str, Engine]:
    models_dir = Path(models_dir)
    engines: list[Engine] = [
        LineartEngine("lineart_realistic", "Lineart – realistic", models_dir / MODEL_FILES["lineart_realistic"]),
        LineartEngine("lineart_coarse", "Lineart – coarse", models_dir / MODEL_FILES["lineart_coarse"]),
        LineartEngine(
            "lineart_anime", "Lineart – anime", models_dir / MODEL_FILES["lineart_anime"], align=256, signed=True
        ),
        DexinedEngine(models_dir / MODEL_FILES["dexined"]),
        ClassicEngine(),
        GeminiEngine(settings_provider),
    ]
    return {engine.id: engine for engine in engines}
