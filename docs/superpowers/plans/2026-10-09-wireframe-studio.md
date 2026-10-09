# Wireframe Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Portable Windows app: color image → line-art wireframe → transparent crisp-black PNG → single-path SVG.

**Architecture:** Pure-function image core (`wireframe_studio/core/`) with no Qt dependency, pluggable
wireframe engines (`wireframe_studio/engines/`), a Qt UI (`wireframe_studio/ui/`) that runs core work
on a thread pool. Models live in a `models/` folder next to the exe and are fetched by
`tools/fetch_models.py` at build time (CI has open internet).

**Tech Stack:** Python 3.12, PySide6-Essentials, onnxruntime, opencv-contrib-python-headless,
numpy, Pillow, potracer, google-genai, pytest, PyInstaller, GitHub Actions (windows-latest).

## Global Constraints

- Background removal output: alpha ∈ {0, 255}; every opaque pixel is exactly #000000.
- SVG output: exactly one `<path>`, fill `#000000`, `fill-rule="evenodd"`, viewBox = image size.
- Nothing is downloaded at runtime except Gemini API calls.
- Default threshold 200; line weights: Natural, 1, 2, 3, 4, 6 px.
- Default Gemini model `gemini-3.1-flash-image` (editable); settings.json next to the exe.
- User sample images are private: never committed (`samples/` is git-ignored).

## Deviations from spec (found during research)

- **TEED / PiDiNet replaced by DexiNed** (MIT, ready-made ONNX from opencv_zoo, run via OpenCV DNN —
  onnxruntime rejects its quantized nodes). TEED/PiDiNet need PyTorch conversion; can be added later.
- "Show 4 options" uses: Lineart realistic, Lineart coarse, Lineart anime, DexiNed.
- Lineart models: ONNX exports from `deepghs/imgutils-models` (Hugging Face), fetched in CI.

## File structure

```
wireframe_studio/
  __main__.py            entry: GUI, or --self-test
  paths.py               app_dir(), models_dir(), settings_path()
  settings.py            Settings dataclass load/save JSON
  core/
    imageio.py           load_rgb(path), save_png(img, path)
    cleanup.py           to_line_map(gray)->uint8 white-bg; remove_background(gray, threshold)->RGBA
    lineweight.py        apply_line_weight(gray, weight: int|None, threshold)->uint8
    vectorize.py         trace_to_svg(rgba, smoothness)->str
  engines/
    base.py              Engine protocol: id, name, available(), run(rgb, variation:int)->gray uint8
    classic.py           XDoG/Canny
    lineart.py           ONNX lineart realistic/coarse/anime (onnxruntime)
    dexined.py           OpenCV DNN DexiNed
    gemini.py            Gemini API engine (prompt per call)
    registry.py          all_engines(models_dir, settings) ; FOUR_OPTIONS ids
  model/card.py          Card state: original, versions, selected, nobg, svg, prompt, invalidation
  ui/main_window.py, ui/card_widget.py, ui/workers.py, ui/settings_dialog.py
tools/fetch_models.py    download models into models/
tests/                   pytest per module
packaging/wireframe_studio.spec, .github/workflows/build.yml
```

## Tasks

### Task 1: Core image ops (cleanup + line weight)
- [ ] Tests: `remove_background` yields only alpha {0,255}, opaque RGB == 0, threshold boundary honored;
      `to_line_map` inverts dark-background maps; `apply_line_weight(img, 3)` on a 1-px diagonal line gives
      a stroke whose measured width (distance transform max*2) ≈ 3; `None` returns binarized input unchanged.
- [ ] Implement with OpenCV (`cv2.ximgproc.thinning` for skeleton, elliptical kernel dilation).
- [ ] Run `pytest tests/test_cleanup.py tests/test_lineweight.py` → PASS. Commit.

### Task 2: Vectorize
- [ ] Tests: SVG parses (xml.etree), one `<path>`, viewBox "0 0 W H", fill black, evenodd; a ring shape keeps
      its hole (path has ≥2 subpaths `M`); empty image → valid SVG with empty path.
- [ ] Implement with `potracer` (`potrace.Bitmap(mask).trace(turdsize=2, alphamax=smoothness, opticurve=True)`),
      emitting absolute `M/C/L/Z` commands. Measure speed on 1000px sample; must be < ~5 s.
- [ ] PASS + commit.

### Task 3: Engines (classic, lineart ONNX, DexiNed, registry) + fetch_models
- [ ] Tests: classic returns HxW uint8 white-bg; lineart engine runs a tiny generated ONNX model (onnx.helper,
      Identity-like conv) with correct pre/post-processing & output size; unavailable when model file missing;
      variation changes detect resolution; registry lists all engines with availability flags.
- [ ] Implement; `tools/fetch_models.py` downloads dexined (media.githubusercontent) + lineart ONNX (HF).
- [ ] PASS + commit.

### Task 4: Gemini engine
- [ ] Tests with a fake client: sends prompt + image, extracts first inline image part, resizes to original
      size, converts to gray; raises `EngineError` with friendly message when no key / API error / no image.
- [ ] Implement with `google.genai.Client(api_key).models.generate_content(model, [prompt, pil_image])`.
- [ ] PASS + commit.

### Task 5: Card model + settings
- [ ] Tests: adding versions selects newest; selecting a version clears nobg/svg; settings roundtrip JSON and
      defaults when file missing/corrupt.
- [ ] Implement. PASS + commit.

### Task 6: UI + workers + self-test
- [ ] Main window per spec layout; card widget (thumbnails, ◀ ▶, Recreate, Save, remove, per-card prompt,
      2×2 grid for 4 options, spinner/error label); QThreadPool workers; drag & drop; Save all; settings dialog.
- [ ] `python -m wireframe_studio --self-test` runs all available local engines + steps 2/3 on a synthetic
      image, exits 0. Offscreen smoke test (`QT_QPA_PLATFORM=offscreen`) builds the window and processes one card.
- [ ] PASS + commit.

### Task 7: Packaging + CI + README
- [ ] PyInstaller one-folder spec including `models/`; workflow on windows-latest: install, fetch models,
      pytest, build, run `WireframeStudio.exe --self-test`, zip, upload artifact; release on `v*` tags.
- [ ] README with download/usage instructions. Push and confirm CI green.
