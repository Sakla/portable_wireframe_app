"""User settings persisted as JSON next to the executable (portable)."""
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

DEFAULT_PROMPT = (
    "from this image I've just uploaded in this message generate a clean, technical line art "
    "illustration using only solid black outlines on a white background. this must be a 2d line "
    "drawing style, not a 3d transparent wireframe. ensure all surfaces are solid and "
    "non-transparent, so you cannot see through one part of the object to another. no shading, "
    "no color or gray tones. just high-contrast black lines. dont use any color, don't add or "
    "remove anything from the picture, make sure that the everything looks exactly like the "
    "picture only wireframe"
)

GEMINI_MODELS = ["gemini-3.1-flash-image", "gemini-3-pro-image"]
LINE_WEIGHTS = [None, 1, 2, 3, 4, 6]  # None = Natural


@dataclass
class Settings:
    gemini_api_key: str = ""
    gemini_model: str = GEMINI_MODELS[0]
    default_prompt: str = DEFAULT_PROMPT
    engine_id: str = "lineart_realistic"
    line_weight: int | None = None
    threshold: int = 200
    smoothness: float = 1.0
    four_options: bool = False
    last_dir: str = ""

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
