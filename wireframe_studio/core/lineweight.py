"""Uniform line weight: thin every line to a 1-px centerline, then thicken it evenly."""
from typing import Optional

import cv2
import numpy as np

from .cleanup import to_gray


def apply_line_weight(gray: np.ndarray, weight: Optional[int], threshold: int = 200) -> np.ndarray:
    """Return a white-background line map whose lines are `weight` px thick.

    weight=None ("Natural") returns the input unchanged so the engine's own
    line weights and anti-aliasing are kept for the background-removal step.
    """
    gray = to_gray(gray)
    if weight is None:
        return gray
    ink = np.where(gray < threshold, 255, 0).astype(np.uint8)
    skeleton = cv2.ximgproc.thinning(ink, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    if weight > 1:
        shape = cv2.MORPH_RECT if weight == 2 else cv2.MORPH_ELLIPSE
        kernel = cv2.getStructuringElement(shape, (weight, weight))
        skeleton = cv2.dilate(skeleton, kernel)
    return np.where(skeleton > 0, 0, 255).astype(np.uint8)
