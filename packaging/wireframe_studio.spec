# PyInstaller spec: one-folder portable build -> dist/WireframeStudio/WireframeStudio.exe
# Models are copied next to the exe by the build workflow (dist/WireframeStudio/models).
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root)],
    datas=[(str(root / "wireframe_studio" / "resources" / "icon.png"), "wireframe_studio/resources")],
    hiddenimports=["google.genai", "potrace"],
    excludes=["tkinter", "matplotlib", "torch", "pytest", "onnx", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WireframeStudio",
    console=False,
    icon=str(root / "packaging" / "icon.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="WireframeStudio", upx=False)
