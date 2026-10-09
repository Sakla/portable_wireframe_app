"""Image file loading/saving with unicode-safe paths (cv2.imread fails on them on Windows)."""
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ImageLoadError(Exception):
    pass


def load_rgb(path) -> np.ndarray:
    """Load any supported image as RGB uint8; transparent areas become white."""
    try:
        with Image.open(path) as img:
            img.load()
            if img.mode in ("RGBA", "LA", "P"):
                rgba = img.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, rgba)
            return np.array(img.convert("RGB"))
    except (OSError, UnidentifiedImageError) as exc:
        raise ImageLoadError(f"Cannot open {Path(path).name}: {exc}") from exc


def save_png(image: np.ndarray, path) -> None:
    Image.fromarray(image).save(path, format="PNG")
