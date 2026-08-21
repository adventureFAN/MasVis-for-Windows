# Third-party source access for the Windows package

This file records exact source-access/build identity for third-party runtime
components shipped with MasVis for Windows 1.0.0.

## Qt for Python / PySide6 6.11.2

Official Qt for Python source archive:

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.zip
- SHA-256: `c0fdd62b91a1d36d5ee2e1fb71050a32fbc93fcdeef0fdcb41d29afaaf00d9b5`

## Qt 6.11.2

Official Qt source archive:

- https://download.qt.io/official_releases/qt/6.11/6.11.2/single/qt-everywhere-src-6.11.2.tar.xz
- SHA-256: `6dcfbca271d76a6502741a2c0dc6fc98ef7dd0b7b4cfd0abcebb285a86a26f33`

The pinned Qt for Python package metadata records
`LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Exact package metadata and
license/notice files from the pinned build environment are collected into the
release bundle.

## FFmpeg / ffprobe 9.0.1 Essentials (Gyan)

Redistributed runtime identity:

- Gyan release: https://github.com/GyanD/codexffmpeg/releases/tag/9.0.1
- exact binary archive: https://github.com/GyanD/codexffmpeg/releases/download/9.0.1/ffmpeg-9.0.1-essentials_build.zip
- binary label: `9.0.1-essentials_build-www.gyan.dev`
- package license: GPLv3
- configuration includes `--enable-gpl --enable-version3 --enable-static`
- FFmpeg source revision named by the package README: `bf1b838f2a`
- FFmpeg source revision: https://github.com/FFmpeg/FFmpeg/commit/bf1b838f2a
- archive SHA-256: `FEC81AE03971D9DD4BE3EBE02E263BD2EC1D789483F931BDBA5F5715E65DA2E9`
- `ffmpeg.exe` SHA-256: `72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3`
- `ffprobe.exe` SHA-256: `19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F`

The exact Gyan package README is preserved as
`vendor/ffmpeg/FFMPEG-GYAN-README.txt` (and copied into the packaged third-party
license directory). It records the complete build configuration and the exact
versions/revisions of the external libraries statically included in the Gyan
binary. The Gyan release identifies the matching FFmpeg source revision.

For redistribution, the public release must keep this source-access file, the
Gyan README and GPLv3 text next to the binary package information. MasVis for
Windows does not claim that its own source archive is the source code of FFmpeg
or of FFmpeg's third-party libraries.

## OpenSSL runtime DLLs

The PySide6/Qt runtime collected by PyInstaller currently includes OpenSSL 3
runtime DLLs (`libcrypto-3.dll` / `libssl-3.dll`). OpenSSL 3.x is licensed under
Apache License 2.0. The Apache-2.0 text is included in the common third-party
license bundle.
