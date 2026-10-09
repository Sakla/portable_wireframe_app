"""Turn engine output into clean black-on-white line maps and transparent PNGs.

remove_background() reproduces the manual GIMP workflow: white -> transparent,
everything else -> solid black, so lines have no grey anti-aliased fringe.
"""
import numpy as np


def to_gray(image: np.ndarray) -> np.ndarray:
    """Convert gray/RGB/RGBA uint8 to gray uint8; transparent pixels become white."""
    if image.ndim == 2:
        return image
    rgb = image[..., :3].astype(np.float32)
    gray = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
    if image.shape[2] == 4:
        alpha = image[..., 3].astype(np.float32) / 255.0
        gray = gray * alpha + 255.0 * (1.0 - alpha)
    return np.clip(gray + 0.5, 0, 255).astype(np.uint8)


def to_line_map(gray: np.ndarray) -> np.ndarray:
    """Normalize a line map to dark lines on a white background.

    Edge detectors output white lines on black; line-art models output the
    opposite. Line drawings are mostly background, so a dark mean means the
    polarity is inverted.
    """
    gray = to_gray(gray)
    if gray.mean() < 128:
        return 255 - gray
    return gray


def remove_background(image: np.ndarray, threshold: int = 200) -> np.ndarray:
    """Return RGBA: pixels with luminance >= threshold are transparent, all others opaque black."""
    gray = to_gray(image)
    ink = gray < threshold
    rgba = np.zeros(gray.shape + (4,), np.uint8)
    rgba[..., 3] = np.where(ink, 255, 0).astype(np.uint8)
    return rgba
