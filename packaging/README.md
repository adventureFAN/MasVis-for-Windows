# Windows packaging notes

The Windows release uses **PyInstaller onedir**, not onefile. This keeps startup
predictable and keeps the bundled FFmpeg/ffprobe executables as ordinary files
inside the application's `_internal` runtime directory.

## Verified packaging baseline

- Python 3.14.7 AMD64
- PyInstaller 6.21.0
- PySide6 / Qt 6.11.2
- NumPy 2.5.2
- SciPy 1.18.0
- Matplotlib 3.11.1
- Pillow 12.3.0
- Gyan FFmpeg 9.0.1 Essentials
  - archive SHA256: `FEC81AE03971D9DD4BE3EBE02E263BD2EC1D789483F931BDBA5F5715E65DA2E9`
  - ffmpeg.exe SHA256: `72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3`
  - ffprobe.exe SHA256: `19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F`
  - required filters verified: `ebur128`, `astats`

## Local packaging test

From PowerShell 7:

```powershell
Set-Location C:\path\to\MasVis-Windows
.\packaging\build_packaging_test.ps1
```

If the verified FFmpeg vendor files are missing, run:

```powershell
.\packaging\fetch_ffmpeg.ps1
```

The build appears under `dist\MasVis-for-Windows\` and is intentionally
self-contained: its `_internal\vendor\ffmpeg\` directory must contain the exact
hash-pinned `ffmpeg.exe` and `ffprobe.exe` binaries.

After final validation, `packaging\create_release_zip.ps1` creates the public
portable ZIP and hard-fails if either bundled FFmpeg executable is missing or
has an unexpected SHA-256 hash.

## License/distribution policy

MasVis for Windows is distributed under **GPL-3.0-or-later**. Reused upstream
MasVisGtk source retains its original GPL-2.0-or-later notices; the upstream
"or later" grant permits distribution of the combined Windows work under GPLv3.

The selected Gyan FFmpeg 9.0.1 Essentials build is GPLv3 and is redistributed as
separate third-party executables inside the portable package. The package ships
GPLv3 text, the exact Gyan build README and source-access/build-identity
information under `THIRD-PARTY-LICENSES\FFmpeg-Gyan-9.0.1\`.

## 1.0.0 validation status

The bundled-FFmpeg onedir path was validated with the established Golden
Vicarious analyses and Dynamics Comparison. The package measured approximately
438.61 MiB unpacked and 177.56 MiB as an Optimal ZIP. A Gyan Full Shared
experiment was rejected because it was larger than the accepted Essentials
Static runtime.
