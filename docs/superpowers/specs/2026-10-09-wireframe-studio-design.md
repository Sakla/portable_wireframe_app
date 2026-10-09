# Wireframe Studio — Design Spec

Date: 2026-10-09
Status: Draft, awaiting user review

## Purpose

A portable Windows desktop app that turns color images into crisp black line-art
("wireframes"), removes the background, and converts the result into a single SVG
vector. It replaces the user's current manual workflow:

1. AI (Gemini) generates line art from a color image.
2. GIMP: add alpha channel, select white, delete it, invert selection, fill black
   (removes the ~1px grey anti-aliasing around lines so they are crisp).
3. Figma "Tracer" plugin converts the image to one vector.

Constraint: at the user's workplace every LLM except Gemini is blocked at the network
level. The app must therefore work fully offline, with Gemini as an optional online engine.

## Technology

- **Language/UI:** Python 3.12 + PySide6 (Qt).
- **Local AI inference:** ONNX Runtime (CPU). Models are bundled inside the app;
  nothing is downloaded at runtime.
- **Image processing:** OpenCV + NumPy (+ scikit-image for skeletonization if needed).
- **Vectorization:** potrace (via a Python binding / pure-Python port).
- **Gemini:** official `google-genai` Python SDK. Model name is a setting with a
  current image-capable default (verified at implementation time).
- **Packaging:** PyInstaller "one-folder" build zipped as `WireframeStudio-<version>-win64.zip`
  containing `WireframeStudio.exe`. No installer, no admin rights.
- **CI:** GitHub Actions on `windows-latest` runs tests and builds the zip on every push;
  zip is uploaded as a workflow artifact, and attached to a GitHub Release on version tags.

## Window layout

```
┌───────────────────────────────────────────────────────────────┐
│ [+ Add images] [Save all]  [1. Wireframe] [2. Remove BG] [3. Vector] │
│ Engine: [Lineart – realistic ▼]  Line weight: [2 px ▼]          │
│ ☐ Show 4 options   Black threshold: ──●── 200   Smoothness: ─●─ │
├───────────────────────────────────────────────────────────────┤
│ ┌─ ☑ chair.jpg ─────────────────────────────────────────────┐ │
│ │ [original] → [result]   ◀ 2/5 ▶  [⟳ Recreate] [Save] [✕]   │ │
│ │ Gemini prompt: [pre-filled default prompt, editable……]      │ │
│ └────────────────────────────────────────────────────────────┘ │
│ ┌─ ☐ lamp.png ──────────────────────────────────────────────┐ │
│ │ ...                                                         │ │
│ └────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────┤
│ Settings: Gemini API key [••••••]  Gemini model [.....]          │
└───────────────────────────────────────────────────────────────┘
```

- Images are added via button or drag-and-drop. One or many. Each image gets its own
  **card**; outputs are never merged.
- The three step buttons act on the **checked** cards, or on all cards if none are checked.
- Each step operates on that card's **current result** of the previous stage. A card
  can be created from an already-made wireframe (e.g. a Gemini web result) and go
  straight to steps 2 and 3.
- **Save** (per card) writes, for whatever stages exist:
  `<name>_wireframe.png`, `<name>_nobg.png` (transparent background), `<name>.svg`.
  **Save all** asks for a folder and saves every card.
- Clicking the result thumbnail opens a larger preview.

## Card state and versions

Each card holds:

- `original` image
- `wireframe_versions`: list of results, with a selected index (◀ n/m ▶)
- `nobg` image (derived from the selected wireframe version)
- `svg` text (derived from `nobg`)
- `gemini_prompt`: per-card text, pre-filled with the default prompt

Changing the selected wireframe version invalidates `nobg`/`svg` for that card
(they are regenerated the next time steps 2/3 run).

## Step 1 — Wireframe engines

Engine dropdown entries (subject to license verification; any model whose license
does not permit this use is dropped):

| Engine | Source | Notes |
|---|---|---|
| Lineart – realistic | Informative Drawings / ControlNet Lineart | Default. Clean outlines of real objects. |
| Lineart – coarse | ControlNet Lineart (coarse) | Bolder, fewer lines. |
| Lineart – anime | ControlNet Lineart Anime / Anime2Sketch | Very clean illustrated look. |
| TEED | TEED edge model | More structural detail. |
| PiDiNet | PiDiNet edge model | Soft edges, good structure. |
| Classic (no AI) | OpenCV (XDoG/Canny) | Instant, for simple graphics. |
| Gemini (online) | Gemini API, image model | Uses the card's prompt box. |

All engines output a grayscale line map; it is then normalized to black lines on a
white background.

### Line weight

Dropdown: **Natural, 1, 2, 3, 4, 6 px**.
For any value other than Natural: binarize → skeletonize to 1-px centerlines →
dilate with a disk of the chosen diameter. Gives uniform line weight regardless of engine.

### Recreate

Re-runs step 1 for that card with the current engine and settings. If nothing changed
since the last run, it uses a **variation**: local engines vary input resolution /
detail threshold (deterministic models need input changes to differ); Gemini simply
generates again. The new result is appended as a new version.

### Show 4 options (checkbox)

When checked, running step 1 or Recreate produces **4 results from 4 different local
engines** (Lineart – realistic, Lineart – coarse, Lineart – anime, TEED), shown in a
2×2 grid in the card. Clicking one selects it. All 4 are added to the version history.

Rationale: local models are deterministic, so 4 variations of one engine differ only
subtly. Comparing different engines side by side is more useful, especially while
learning which engine suits which kind of image. Gemini is not included in the grid
(slower, costs per call); it runs only when chosen in the dropdown.

## Step 2 — Remove background (GIMP replica)

Input: selected wireframe version (or a dropped-in image).
1. Convert to grayscale.
2. Pixels with luminance **≥ threshold** (default 200, slider) → fully transparent.
3. All other pixels → pure black `#000000`, alpha 255.
Result: RGBA PNG with only two pixel states (transparent or opaque black); no grey,
no semi-transparent edge.

## Step 3 — Vector (Tracer replica)

Input: `nobg` image.
1. Opaque-black mask → potrace bitmap.
2. Trace with Tracer-like defaults (turd size ~2, alphamax ~1.0, curve optimization on);
   **Smoothness** slider maps to alphamax.
3. Emit an SVG with the image's width/height/viewBox containing **one `<path>`**
   (all curves combined, fill `#000000`, even-odd fill rule so holes are preserved).

## Gemini integration

- API key and model name are entered in Settings and stored in `settings.json`
  **next to the .exe** (portable; plain text — the UI notes this).
- Default prompt (user's own, pre-filled into every new card's prompt box):

  > from this image I've just uploaded in this message generate a clean, technical
  > line art illustration using only solid black outlines on a white background. this
  > must be a 2d line drawing style, not a 3d transparent wireframe. ensure all surfaces
  > are solid and non-transparent, so you cannot see through one part of the object to
  > another. no shading, no color or gray tones. just high-contrast black lines. dont
  > use any color, don't add or remove anything from the picture, make sure that the
  > everything looks exactly like the picture only wireframe

- The default prompt is editable in Settings.
- The returned image is resized to the original's dimensions so later steps and the
  SVG match the source size.

## Error handling and responsiveness

- All processing runs in a background worker pool; the UI never freezes. Each card
  shows a spinner while working.
- Errors are shown **on the affected card** (e.g. "Gemini: invalid API key",
  "Gemini: network blocked"); other cards are unaffected.
- Unsupported/corrupt image files are rejected with a message at import.
- Supported inputs: PNG, JPG/JPEG, WEBP, BMP.

## Testing

- Unit tests (pytest) for pure image functions:
  - background removal leaves only alpha∈{0,255} and RGB=black on opaque pixels;
  - line weight produces lines of the requested thickness on synthetic shapes;
  - tracing yields valid SVG with exactly one `<path>` and correct viewBox;
  - each local engine loads and returns an image of the input's size.
- Gemini client tested with a mocked SDK.
- CI runs tests on Windows before building; a smoke test launches the packaged exe
  with `--self-test` (processes a sample image headlessly and exits 0).

## Out of scope (future)

- Natural-language instructions for the local engines.
- Batch presets / remembering engine choice per image type.
- GPU acceleration.
