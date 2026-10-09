"""ControlNet line-art models (Informative Drawings / Anime2Sketch) via ONNX Runtime."""
import threading
from pathlib import Path

import numpy as np

from .base import Engine, EngineError, detect_resolution, float_to_gray, resize_back, resize_for_model


class LineartEngine(Engine):
    """`signed` models take/return values in [-1, 1] instead of [0, 1]."""

    def __init__(self, engine_id: str, name: str, model_path: Path, align: int = 64, signed: bool = False):
        self.id = engine_id
        self.name = name
        self.model_path = Path(model_path)
        self.align = align
        self.signed = signed
        self._session = None
        self._lock = threading.Lock()

    def available(self):
        return self.model_path.is_file()

    def unavailable_reason(self):
        return f"model file missing: models/{self.model_path.name}"

    def _get_session(self):
        with self._lock:
            if self._session is None:
                import onnxruntime as ort

                options = ort.SessionOptions()
                options.log_severity_level = 3
                self._session = ort.InferenceSession(
                    str(self.model_path), options, providers=["CPUExecutionProvider"]
                )
            return self._session

    def run(self, rgb, variation=0, prompt=""):
        if not self.available():
            raise EngineError(f"{self.name}: {self.unavailable_reason()}")
        height, width = rgb.shape[:2]
        resized = resize_for_model(rgb, detect_resolution(variation), self.align).astype(np.float32)
        tensor = resized / 127.5 - 1.0 if self.signed else resized / 255.0
        tensor = tensor.transpose(2, 0, 1)[None, ...].astype(np.float32)
        session = self._get_session()
        output = session.run(None, {session.get_inputs()[0].name: tensor})[0][0, 0]
        if self.signed:
            output = (output + 1.0) / 2.0
        return resize_back(float_to_gray(output), height, width)
