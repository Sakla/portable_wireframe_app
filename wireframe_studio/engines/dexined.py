"""DexiNed edge detector (opencv_zoo ONNX), run with OpenCV DNN.

onnxruntime rejects this model's quantized nodes; OpenCV DNN runs it at any
input size that is a multiple of 32.
"""
import threading
from pathlib import Path

import cv2
import numpy as np

from .base import Engine, EngineError, detect_resolution, resize_back, resize_for_model


class DexinedEngine(Engine):
    id = "dexined"
    name = "DexiNed (edges)"

    def __init__(self, model_path: Path):
        self.model_path = Path(model_path)
        self._net = None
        self._lock = threading.Lock()

    def available(self):
        return self.model_path.is_file()

    def unavailable_reason(self):
        return f"model file missing: models/{self.model_path.name}"

    def run(self, rgb, variation=0, prompt=""):
        if not self.available():
            raise EngineError(f"{self.name}: {self.unavailable_reason()}")
        height, width = rgb.shape[:2]
        bgr = cv2.cvtColor(resize_for_model(rgb, detect_resolution(variation), 32), cv2.COLOR_RGB2BGR)
        blob = cv2.dnn.blobFromImage(bgr, 1.0, (bgr.shape[1], bgr.shape[0]), (103.5, 116.2, 123.6))
        with self._lock:  # cv2.dnn.Net is not thread-safe
            if self._net is None:
                self._net = cv2.dnn.readNetFromONNX(str(self.model_path))
            self._net.setInput(blob)
            outputs = self._net.forward(self._net.getUnconnectedOutLayersNames())
        fused = np.squeeze(outputs[-1])
        edges = 1.0 / (1.0 + np.exp(-fused))
        edges = cv2.normalize(edges, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        return resize_back(255 - edges, height, width)
