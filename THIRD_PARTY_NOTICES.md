# Third-party notices

MasVis for Windows is distributed under GPL-3.0-or-later and uses or builds upon
several third-party projects. This file is an attribution summary, not a
replacement for the license texts distributed by those projects.

## MasVisGtk

- Project: MasVisGtk
- Upstream: https://github.com/itprojects/MasVisGtk
- Copyright notices in the reused source files are preserved.
- License: GNU General Public License, version 2 or later as stated in the
  upstream source headers. Those original notices remain preserved. Because the
  upstream grant permits "version 2 or later", the MasVis for Windows combined
  distribution is released under GPL-3.0-or-later; the repository `LICENSE` is
  GPLv3.

MasVisGtk builds upon PyMasVis by Joakim Fors, a Python reimplementation of the
original MasVis. Those lineage credits are preserved in the application and
README.

## Microsoft Fluent UI System Icons

- Project: Microsoft Fluent UI System Icons
- License: MIT
- Selected SVG assets and the MIT license text are bundled under
  `assets/icons/fluent/`.

## Qt for Python / PySide6

- Project: Qt for Python (PySide6 / Shiboken6)
- Project site: https://doc.qt.io/qtforpython-6/
- Qt for Python is offered under open-source licenses including LGPLv3/GPLv3
  as well as commercial licensing; packaged releases must preserve the
  applicable Qt/PySide license notices and corresponding obligations.

## NumPy

- Project: NumPy
- Project site: https://numpy.org/
- License: BSD-3-Clause (see the license shipped by the installed package).

## SciPy

- Project: SciPy
- Project site: https://scipy.org/
- License: BSD-3-Clause (see the license shipped by the installed package).

## Matplotlib

- Project: Matplotlib
- Project site: https://matplotlib.org/
- License: Matplotlib's PSF-compatible open-source license; packaged releases
  must include the license shipped by the installed package.

## Pillow

- Project: Pillow
- Project site: https://python-pillow.github.io/
- License: HPND-style Pillow license; packaged releases must include the
  license shipped by the installed package.

## FFmpeg / ffprobe

MasVis for Windows calls `ffmpeg` and `ffprobe` as external executables for
media probing/decoding and compact comparison time-series extraction. The
portable Windows release redistributes the exact validated Gyan binaries inside
`_internal/vendor/ffmpeg/`; the application does not use an arbitrary system
FFmpeg when frozen.

Validated redistributed runtime identity:

- Gyan FFmpeg **9.0.1 Essentials** (`9.0.1-essentials_build-www.gyan.dev`);
- upstream binary release: https://github.com/GyanD/codexffmpeg/releases/tag/9.0.1
- package license: **GPLv3**;
- build configuration includes `--enable-gpl --enable-version3 --enable-static`;
- FFmpeg source revision identified by the package: `bf1b838f2a`;
- FFmpeg source: https://github.com/FFmpeg/FFmpeg/commit/bf1b838f2a
- archive SHA256: `FEC81AE03971D9DD4BE3EBE02E263BD2EC1D789483F931BDBA5F5715E65DA2E9`;
- `ffmpeg.exe` SHA256: `72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3`;
- `ffprobe.exe` SHA256: `19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F`.

The exact Gyan build README is preserved with the release. It records the full
build configuration, enabled components, external libraries and their exact
versions/revisions. GPLv3 text and source-access information are included under
`THIRD-PARTY-LICENSES/FFmpeg-Gyan-9.0.1/`.

The Gyan FFmpeg binaries are separate third-party executables. Their own
copyrights and license terms remain in force; MasVis for Windows does not claim
authorship of FFmpeg.

## Packaging legal-audit note (2026-08-21)

The Windows binary package stages the exact Python-package license/notice files found in the pinned build environment and records each distribution's license metadata. Standard GPLv3, LGPLv3 and Apache-2.0 texts are also bundled explicitly because some binary wheels do not carry a complete open-source license-text set in their installed metadata.

The PySide6/Qt runtime collected by the current Windows build also contains OpenSSL 3 runtime DLLs; OpenSSL 3.x is covered by Apache License 2.0 and that license text is included in the release license bundle.

The official MasVis for Windows portable release ZIP contains the exact validated Gyan FFmpeg 9.0.1 Essentials object code described above. The exact upstream binary identity, source revision, build README, hashes and source-access information are documented for redistribution. See `packaging/THIRD_PARTY_SOURCE.md`.
