# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path(SPECPATH)

required_paths = [
    project_root / "assets",
    project_root / "src" / "gtk",
    project_root / "vendor" / "ffmpeg" / "ffmpeg.exe",
    project_root / "vendor" / "ffmpeg" / "ffprobe.exe",
]
missing = [str(path) for path in required_paths if not path.exists()]
if missing:
    raise SystemExit(
        "Packaging prerequisites are missing:\n  - " + "\n  - ".join(missing)
    )

block_cipher = None

analysis = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets"), "assets"),
        (str(project_root / "src" / "gtk"), "src/gtk"),
        (str(project_root / "vendor" / "ffmpeg" / "ffmpeg.exe"), "vendor/ffmpeg"),
        (str(project_root / "vendor" / "ffmpeg" / "ffprobe.exe"), "vendor/ffmpeg"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="MasVis-for-Windows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project_root / "assets" / "app" / "masvis-for-windows.ico"),
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="MasVis-for-Windows",
)
