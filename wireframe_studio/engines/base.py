"""Common interface for wireframe engines.

An engine turns an RGB uint8 image (H x W x 3) into a grayscale uint8 line map
of the same size with dark lines on a white background.
"""
import math

import cv2
import numpy as np


class EngineError(Exception):
    """A user-facing failure (shown on the image card)."""


class Engine:
    id = ""
    name = ""
    online = False

    def available(self) -> bool:
        return True

    def unavailable_reason(self) -> str:
        return ""

    def run(self, rgb: np.ndarray, variation: int = 0, prompt: str = "") -> np.ndarray:
        raise NotImplementedError


# Recreate cycles through these detection resolutions (short image side, in px).
DETECT_RESOLUTIONS = [768, 512, 1024, 640, 896]


def detect_resolution(variation: int) -> int:
    return DETECT_RESOLUTIONS[variation % len(DETECT_RESOLUTIONS)]


def resize_for_model(rgb: np.ndarray, resolution: int, align: int) -> np.ndarray:
    """Resize so the short side is ~resolution and both sides are multiples of align."""
    height, width = rgb.shape[:2]
    scale = resolution / min(height, width)
    new_h = max(align, int(math.ceil(height * scale / align)) * align)
    new_w = max(align, int(math.ceil(width * scale / align)) * align)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(rgb, (new_w, new_h), interpolation=interpolation)


def resize_back(gray: np.ndarray, height: int, width: int) -> np.ndarray:
    interpolation = cv2.INTER_AREA if gray.shape[0] > height else cv2.INTER_CUBIC
    return cv2.resize(gray, (width, height), interpolation=interpolation)


def float_to_gray(values: np.ndarray) -> np.ndarray:
    return (np.clip(values, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
