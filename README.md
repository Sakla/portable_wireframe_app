# Wireframe Studio

A portable Windows app that turns color images into crisp black line art, removes the
background, and converts the result into a single-path SVG. It works offline; Gemini is
an optional online engine.

```
[+ Add images]  [1. Wireframe] → [2. Remove BG] → [3. Vector]
```

- **1. Wireframe** – offline AI line-art models (Lineart realistic / coarse / anime, DexiNed),
  a classic non-AI filter, or Gemini with a per-image prompt. *Show 4 options* compares four
  offline engines side by side. *Recreate* makes a new version; ◀ ▶ switches between versions.
  *Line weight* (Natural, 1–6 px) makes every line the same thickness.
- **2. Remove BG** – the GIMP routine, automated: pixels lighter than the *black threshold* become
  transparent, everything else solid black, with no grey anti-aliased edge.
- **3. Vector** – Potrace tracing into one `<path>` (even-odd fill), like Figma's Tracer plugin.
- Each image stays separate: `NAME_wireframe.png`, `NAME_nobg.png`, `NAME.svg`.

## Download

Open the repository's **Actions** tab → latest **Build Windows app** run → download the
`WireframeStudio-win64` artifact. Unzip it twice (GitHub wraps the zip in another zip) and run
`WireframeStudio/WireframeStudio.exe`. Tagged versions (`v*`) are also published under **Releases**.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
python tools/fetch_models.py          # downloads the offline models into ./models
python -m pytest -q
python -m wireframe_studio            # run the app
python -m wireframe_studio --self-test
pyinstaller packaging/wireframe_studio.spec   # portable build in dist/WireframeStudio
```

Code layout: `wireframe_studio/core` (image processing, no UI), `engines` (wireframe engines),
`model` (per-image state), `ui` (PySide6). Design spec and plan are in `docs/superpowers/`.
Model sources and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
