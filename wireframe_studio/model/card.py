"""State of one image card: original, wireframe versions, and derived outputs."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from ..core.cleanup import to_gray, to_line_map
from ..core.imageio import save_png
from ..core.lineweight import apply_line_weight


@dataclass
class Version:
    raw: np.ndarray  # engine output, dark lines on white, before line weight
    engine_id: str
    engine_name: str
    variation: int


@dataclass
class Card:
    name: str  # output file stem, unique within the session
    original: np.ndarray  # RGB uint8
    prompt: str = ""
    versions: list[Version] = field(default_factory=list)
    selected: int = -1
    nobg: Optional[np.ndarray] = None  # RGBA
    svg: Optional[str] = None
    choice: list[int] = field(default_factory=list)  # version indices shown in the 4-options grid

    def add_versions(self, versions: list[Version], as_choice: bool = False) -> None:
        start = len(self.versions)
        self.versions.extend(versions)
        self.choice = list(range(start, len(self.versions))) if as_choice else []
        self.select(start if as_choice else len(self.versions) - 1)

    def select(self, index: int) -> None:
        if not 0 <= index < len(self.versions):
            raise IndexError(index)
        if index != self.selected:
            self.selected = index
            self.invalidate_outputs()

    def pick_choice(self, index: int) -> None:
        self.select(index)
        self.choice = []

    def invalidate_outputs(self) -> None:
        self.nobg = None
        self.svg = None

    def next_variation(self, engine_id: str) -> int:
        """Recreating with the same engine tries the next variation."""
        return sum(1 for v in self.versions if v.engine_id == engine_id)

    @property
    def current_version(self) -> Optional[Version]:
        return self.versions[self.selected] if self.versions else None

    def wireframe(self, weight: Optional[int], threshold: int) -> np.ndarray:
        """Selected version with the line weight applied; the original if no version yet."""
        source = self.current_version.raw if self.versions else to_gray(self.original)
        return apply_line_weight(to_line_map(source), weight, threshold)

    def save(self, folder: Path, weight: Optional[int], threshold: int) -> list[Path]:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        written = []
        if self.versions:
            path = folder / f"{self.name}_wireframe.png"
            save_png(self.wireframe(weight, threshold), path)
            written.append(path)
        if self.nobg is not None:
            path = folder / f"{self.name}_nobg.png"
            save_png(self.nobg, path)
            written.append(path)
        if self.svg is not None:
            path = folder / f"{self.name}.svg"
            path.write_text(self.svg, encoding="utf-8")
            written.append(path)
        return written


def unique_name(stem: str, taken: set[str]) -> str:
    name, n = stem, 2
    while name in taken:
        name = f"{stem} ({n})"
        n += 1
    return name
