# MasVis for Windows 1.0.0 — release notes

## MasVis, native on Windows

MasVis for Windows is an independent Windows-native fork of MasVisGtk by ITProjects. MasVisGtk builds on PyMasVis by Joakim Fors, a Python reimplementation of the original MasVis.

The Windows fork preserves the established MasVis analysis/report concepts while replacing the GTK/libadwaita desktop interface with a native PySide6/Qt application.

## Highlights

- Detailed MasVis analysis reports with waveform, spectrum, crest, histogram, Peak-vs-RMS, EBU R128 and TT-style DR information.
- Dynamics Assessment v1 with explainable Level Maximization Evidence scoring.
- Dynamics Comparison v1 with same-content alignment, level matching, Loudness Dynamics Similarity, Loudness Dynamics Advantage and separate Peak Structure Difference.
- Multi-tab workflow, Advanced Open, Overview modes and drag & drop.
- Compare Selected / Compare All plus animated GIF export.
- Light/Dark application and report presentation.
- High-resolution report export.
- Windows-native preferences, file information, help/shortcuts and About UI.
- Hash-pinned Gyan FFmpeg 9.0.1 Essentials runtime bundled directly with the portable Windows release.
- Validated bounded-memory True Peak path that materially reduces temporary RAM use on eligible input without changing accepted reference results.

## Important interpretation notes

Dynamics Assessment is a deterministic evidence score, not a probability of mastering history and not a sound-quality grade.

Dynamics Comparison is designed for two versions of substantially the same material. Loudness Dynamics Similarity describes aligned EBU R128 Short-Term loudness development; it does not claim that transient, crest or peak dynamics are identical. Peak Structure Difference remains a separate dimension.

## Distribution

The Windows release is a self-contained portable x64 ZIP. Python, Qt, the Python runtime dependencies and the exact validated Gyan FFmpeg 9.0.1 Essentials `ffmpeg.exe` / `ffprobe.exe` binaries are included. Extract the ZIP and start `MasVis-for-Windows.exe`; no separate FFmpeg installation, setup helper or PATH configuration is required.

## Credits

MasVis for Windows would not exist without MasVisGtk, PyMasVis and the original MasVis lineage. Upstream copyright and license notices remain preserved.

## License

MasVis for Windows is distributed under GPL-3.0-or-later. Packaged third-party runtime components retain their own licenses and notices. See `THIRD_PARTY_NOTICES.md`.
