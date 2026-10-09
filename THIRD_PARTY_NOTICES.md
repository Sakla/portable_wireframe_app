# Third-party models

Wireframe Studio bundles these offline models (downloaded at build time by `tools/fetch_models.py`):

| File | Model | Upstream | License |
|---|---|---|---|
| `lineart.onnx`, `lineart_coarse.onnx` | ControlNet 1.1 line-art annotators (Informative Drawings architecture) | [lllyasviel/ControlNet](https://github.com/lllyasviel/ControlNet), [carolineec/informative-drawings](https://github.com/carolineec/informative-drawings) | Apache-2.0 / MIT |
| `lineart_anime.onnx` | Anime2Sketch generator as used by ControlNet 1.1 | [Mukosame/Anime2Sketch](https://github.com/Mukosame/Anime2Sketch) | MIT |
| `dexined.onnx` | DexiNed edge detector | [xavysp/DexiNed](https://github.com/xavysp/DexiNed), ONNX from [opencv/opencv_zoo](https://github.com/opencv/opencv_zoo) | MIT |

ONNX exports of the line-art models come from [deepghs/imgutils-models](https://huggingface.co/deepghs/imgutils-models).

Python libraries: PySide6 (LGPL-3.0), ONNX Runtime (MIT), OpenCV (Apache-2.0), NumPy (BSD),
Pillow (MIT-CMU), potracer (GPL-2.0, a port of Potrace), google-genai (Apache-2.0).
