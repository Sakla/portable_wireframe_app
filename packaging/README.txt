Wireframe Studio — portable
===========================

Run WireframeStudio.exe. No installation needed; keep this whole folder together
(the "models" folder holds the offline AI models).

1. Add images (button or drag & drop). Each image gets its own card.
2. "1. Wireframe"  – makes line art with the engine chosen in the dropdown.
   "Show 4 options" compares 4 offline engines; click the one you like.
   "Recreate" on a card makes another version; use ◀ ▶ to switch versions.
3. "2. Remove BG"  – white becomes transparent, lines become solid black (no grey edge).
4. "3. Vector"     – traces the lines into one SVG path.
5. "Save" / "Save all" – writes NAME_wireframe.png, NAME_nobg.png and NAME.svg.

Tick cards to run the step buttons only on those; with none ticked, all cards are used.

Gemini (optional, online): Settings… -> paste an API key from aistudio.google.com,
then choose "Gemini (online)" in the Engine dropdown. Each card gets its own prompt box.
Settings are saved in settings.json in this folder (the API key is stored in plain text).
