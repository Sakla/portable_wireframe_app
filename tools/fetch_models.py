"""Download the offline wireframe models into ./models (run at build time, needs internet).

Usage: python tools/fetch_models.py [--dest models] [--only dexined,lineart]
"""
import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

HF = "https://huggingface.co/deepghs/imgutils-models/resolve/main/lineart"
MODELS = {
    # ControlNet 1.1 line-art annotators (Informative Drawings / Anime2Sketch), ONNX by deepghs.
    "lineart.onnx": f"{HF}/lineart.onnx",
    "lineart_coarse.onnx": f"{HF}/lineart_coarse.onnx",
    "lineart_anime.onnx": f"{HF}/lineart_anime.onnx",
    # DexiNed (MIT), from the OpenCV model zoo.
    "dexined.onnx": "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/edge_detection_dexined/edge_detection_dexined_2024sep.onnx",
}


def download(url: str, target: Path) -> None:
    tmp = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "wireframe-studio-build"})
    with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out, length=1 << 20)
    if tmp.stat().st_size < 100_000:
        tmp.unlink()
        raise RuntimeError(f"{url} returned a suspiciously small file")
    tmp.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", default=str(Path(__file__).resolve().parents[1] / "models"))
    parser.add_argument("--only", default="", help="comma-separated name prefixes")
    args = parser.parse_args()
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    prefixes = [p for p in args.only.split(",") if p]
    failed = []
    for name, url in MODELS.items():
        if prefixes and not any(name.startswith(p) for p in prefixes):
            continue
        target = dest / name
        if target.is_file():
            print(f"exists   {name}")
            continue
        try:
            download(url, target)
            print(f"fetched  {name} ({target.stat().st_size // 1024} KB)")
        except Exception as exc:  # report all failures, then exit non-zero
            print(f"FAILED   {name}: {exc}", file=sys.stderr)
            failed.append(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
