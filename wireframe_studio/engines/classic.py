"""Non-AI line extraction (XDoG). Instant; best on simple, clean graphics."""
import cv2
import numpy as np

from .base import Engine

# (sigma, sharpness, epsilon) per Recreate variation
_PARAMS = [(1.0, 100.0, 0.0), (0.7, 80.0, 0.0), (1.4, 120.0, -0.005), (1.0, 200.0, -0.01)]


class ClassicEngine(Engine):
    id = "classic"
    name = "Classic (no AI)"

    def run(self, rgb, variation=0, prompt=""):
        sigma, sharpness, epsilon = _PARAMS[variation % len(_PARAMS)]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        dog = cv2.GaussianBlur(gray, (0, 0), sigma) - 0.98 * cv2.GaussianBlur(gray, (0, 0), sigma * 1.6)
        lines = np.where(dog >= epsilon, 1.0, 1.0 + np.tanh(sharpness * (dog - epsilon)))
        return (np.clip(lines, 0, 1) * 255).astype(np.uint8)
