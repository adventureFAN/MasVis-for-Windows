# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Small command-line sanity check for the Windows analysis path."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from audio_loader import load_audio, scalar
from src.analysis import analyze


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print('  python smoke_test.py "C:\\path\\to\\file.flac"')
        raise SystemExit(1)

    path = Path(sys.argv[1]).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(path)

    print()
    print(f"File: {path.name}")
    print("Decoding audio with FFmpeg ...")

    track = load_audio(path)

    print(
        f"{track['samplerate']} Hz / "
        f"{track['bitdepth']} bit / "
        f"{track['channels']} channels"
    )
    print("Running MasVis analysis ...")
    print()

    result = analyze(track)

    print("========================================")
    print(" MasVis for Windows - Smoke Test")
    print("========================================")
    print(f"DR:          {result['dr']:.1f}")
    print(f"LUFS-I:      {scalar(result['l_kg']):.2f}")
    print(f"LRA:         {scalar(result['lra']):.2f} LU")
    print(f"PLR:         {scalar(result['plr_lu']):.2f} LU")
    print(f"Crest:       {scalar(result['crest_total_db']):.2f} dB")
    print(
        "True Peak:   "
        f"{float(np.max(result['true_peak_dbtp'])):.2f} dBTP"
    )
    print("========================================")
    print()


if __name__ == "__main__":
    main()
