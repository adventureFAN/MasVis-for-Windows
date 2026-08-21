# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Resolve the FFmpeg tools used by MasVis for Windows.

Packaged builds always use the FFmpeg/ffprobe binaries bundled under
``vendor/ffmpeg``.  Source checkouts prefer those verified local binaries when
present and otherwise fall back to PATH for developer convenience.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


_TOOL_DIR = Path("vendor") / "ffmpeg"


def _runtime_root() -> Path:
    """Return the PyInstaller bundle root or the source project root."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parent


def _bundled_tool(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return _runtime_root() / _TOOL_DIR / f"{name}{suffix}"


def _resolve_tool(name: str) -> str:
    bundled = _bundled_tool(name)
    if bundled.is_file():
        return str(bundled)

    # A frozen build is required to be self-contained.  Silently falling back
    # to a machine-wide FFmpeg would make release behavior depend on the host.
    if getattr(sys, "frozen", False):
        raise FileNotFoundError(
            f"The packaged {name} executable is missing: {bundled}"
        )

    discovered = shutil.which(name)
    if discovered:
        return discovered

    raise FileNotFoundError(
        f"{name} was not found. Install FFmpeg on PATH or place the verified "
        f"binary under {_TOOL_DIR}."
    )


def ffmpeg_executable() -> str:
    return _resolve_tool("ffmpeg")


def ffprobe_executable() -> str:
    return _resolve_tool("ffprobe")


def subprocess_window_kwargs() -> dict[str, int]:
    """Prevent helper-console flashes in Windows GUI builds."""
    if os.name != "nt":
        return {}
    return {
        "creationflags": int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    }
