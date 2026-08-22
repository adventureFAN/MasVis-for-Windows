# MasVis for Windows

<p align="center">
  <img src="assets/app/masvis-for-windows.png" alt="MasVis for Windows icon" width="128">
</p>

<p align="center">
  <strong>See what loudness, limiting, headroom and dynamics are actually doing.</strong>
</p>

**MasVis for Windows** is an independent Windows-native fork of
[MasVisGtk](https://github.com/itprojects/MasVisGtk) by ITProjects. MasVisGtk
builds on PyMasVis by Joakim Fors, a Python reimplementation of the original
MasVis.

It keeps the proven MasVis/PyMasVis analysis and report concepts while replacing
the GTK/libadwaita desktop interface with a native PySide6/Qt application for
Windows. On top of the classic report, MasVis for Windows adds explainable tools
for interpreting one master and comparing two versions of the same music.

> ## **We don't replace DR. We explain it.**

![MasVis for Windows main window](assets/screenshots/main-window.png)

## Try it yourself with *Eternal Desert*

MasVis for Windows includes **three controlled demo files** built from the same
track. You can listen to them, analyze them separately, and reproduce very
different Dynamics Comparison cases yourself.

- 🎧 **[Eternal Desert — Reference](examples/Eternal%20Desert%20-%20Reference.mp3)**
- 🔥 **[Eternal Desert — Loudness War](examples/Eternal%20Desert%20-%20Loudness%20War.mp3)**
- 💿 **[Eternal Desert — Vinyl-like transfer simulation](examples/Eternal%20Desert%20-%20Loudness%20War%20%28Vinyl%20Remaster%29.mp3)**

(*Eternal Desert* is an AI-assisted song created with Suno from **lyrics and
creative prompting by adventureFAN**. The Loudness War version is deliberately
louder and more heavily limited. The third file starts from that already
compressed Loudness War master and applies a simplified vinyl-like transfer
chain that changes peak/crest structure without restoring the lost loudness
dynamics.)

That gives the project three complementary demonstrations:

- **Reference vs Loudness War:** DR **10.4 → 6.5**, with a real reduction in
  aligned loudness dynamics.
- **Loudness War vs Vinyl-like transfer:** DR **6.5 → 10.4**, while Loudness
  Dynamics Similarity remains **99.3 / 100**, Loudness Curve Similarity is
  **99.77%**, and **no Loudness Dynamics Advantage** is detected.
- **Reference vs Vinyl-like transfer:** both versions measure **DR 10.4**, yet
  Loudness Dynamics Similarity is only **62.9 / 100** and Version A shows a
  **Strong Loudness Dynamics Advantage**.

Together, these controlled cases show why measured DR and aligned loudness
dynamics should be interpreted as related but distinct properties of the signal.
The example audio is separately cleared demonstration media and is **not covered
by the project's GPL-3.0-or-later source-code license**. See
[`examples/README.md`](examples/README.md) for the exact purpose, processing and
licensing notes.

## Why use MasVis for Windows?

Two releases of the same song can sound and measure very differently. One may be
quieter with more headroom, another may be pushed louder with compression or
limiting, and a vinyl or captured version can show different peaks even when its
underlying musical dynamics are very similar.

This is part of why discussions around the **Loudness War** became so focused on
DR values: they are useful, but one number cannot describe every kind of dynamic
change.

MasVis for Windows helps separate those ideas instead of turning them into one
"good" or "bad" score:

- **How loud is the track overall?**
- **How much peak/headroom-based dynamic range does it measure?**
- **Does the waveform show signs commonly associated with strong level
  maximization or limiting?**
- **If two masters measure differently, is the difference mainly level,
  loudness dynamics over time, peak/crest structure, or a combination?**

The goal is not to tell you which master you should prefer. It is to make the
measurements easier to understand.

## Three ways to look at dynamics

### 1. Classic MasVis analysis

Analyze a track and get the familiar detailed MasVis report: waveform, spectrum,
crest factor, peak-vs-RMS behavior, EBU R128 loudness, TT-style DR, True Peak,
LRA, PLR and more.

**DR remains visible exactly because it is useful.** MasVis for Windows simply
adds more context around it instead of treating DR as a universal quality score.

### 2. Dynamics Assessment

**Simple question:** *How strongly does this waveform show measurable signs
associated with level maximization and strong limiting?*

Dynamics Assessment combines several already-measured indicators into an
explainable **Level Maximization Evidence** score from 0 to 100 and shows which
measurements contributed to it.

![Dynamics Assessment](assets/screenshots/dynamics-assessment.png)

The result is deterministic and transparent, but it is **not** a probability
that a track was mastered in a particular way and **not** a sound-quality grade.
TT-style DR and LRA remain visible as context and do not directly add score
points.

For the frozen v1 methodology, see
[docs/DYNAMICS-ASSESSMENT-V1.md](docs/DYNAMICS-ASSESSMENT-V1.md).

### 3. Dynamics Comparison

**Simple question:** *If two versions of the same music measure differently,
what is actually different — mainly their level, their loudness dynamics over
time, their peak/crest structure, or some combination of those?*

Dynamics Comparison aligns two versions of substantially the same material,
level-matches them, and then keeps several different measurements separate:

- **Measured DR** — the normal MasVis/TT-style DR result for each version.
- **Loudness Dynamics Similarity (LDS)** — a 0-100 point score describing how
  similarly the aligned Short-Term loudness develops over time.
- **Loudness Curve Similarity** — the direct Pearson correlation of those
  aligned Short-Term loudness curves, shown as a percentage.
- **Loudness Dynamics Advantage** — whether one version shows a wider aligned
  loudness-dynamics span.
- **Peak Structure Difference** — a separate 0-100 point description of how
  strongly peak/crest structure differs after alignment and level matching.

![Dynamics Comparison](assets/screenshots/dynamics-comparison-diff-dr.png)

**Want to reproduce this exact comparison?** Use the included
[Loudness War](examples/Eternal%20Desert%20-%20Loudness%20War.mp3) and
[Vinyl-like transfer simulation](examples/Eternal%20Desert%20-%20Loudness%20War%20%28Vinyl%20Remaster%29.mp3)
versions of *Eternal Desert*, then run **Dynamics Comparison**. The screenshot
shows **DR 6.5 vs 10.4** even though the aligned loudness development remains
essentially unchanged.

A large DR difference can coexist with very similar loudness development if the
main difference is concentrated in peaks, crest factor or transient structure.
The application intentionally does not collapse those dimensions into a claim of
"real" or "fake" dynamics.

For the frozen v1 methodology, see
[docs/DYNAMICS-COMPARISON-V1.md](docs/DYNAMICS-COMPARISON-V1.md).

## Three controlled *Eternal Desert* experiments

### 1. Loudness War: lower DR with genuinely reduced loudness dynamics

🎧 **Listen / download:**
[Reference MP3](examples/Eternal%20Desert%20-%20Reference.mp3) ·
[Loudness War MP3](examples/Eternal%20Desert%20-%20Loudness%20War.mp3)

The Loudness War version was deliberately made much louder and denser from the
Reference as a controlled level-maximization stress test. MasVis for Windows
reports **DR 10.4 vs 6.5**, with the Loudness War version about **6.70 dB louder**
after alignment and a clear reduction in aligned Short-Term loudness dynamics.

This is the familiar case where a much lower DR value coincides with a real
change in the song's measured loudness dynamics.

### 2. Vinyl-like transfer: higher DR without restored loudness dynamics

💿 **Listen / download:**
[Loudness War MP3](examples/Eternal%20Desert%20-%20Loudness%20War.mp3) ·
[Vinyl-like transfer simulation](examples/Eternal%20Desert%20-%20Loudness%20War%20%28Vinyl%20Remaster%29.mp3)

For the second experiment, the already compressed **DR 6.5 Loudness War master**
was processed through a deliberately simplified vinyl-like transfer chain. No
expansion or dynamic restoration was applied. Nevertheless, its measured DR
rises to **10.4** — matching the **10.4** of the original Reference.

![Higher measured DR without restored loudness dynamics](assets/screenshots/dynamics-comparison.png)

MasVis for Windows simultaneously reports:

- **Loudness Dynamics Similarity: 99.3 / 100 — Extremely High**;
- **Loudness Curve Similarity: 99.77%**;
- **Loudness Dynamics Advantage: None detected**;
- **Peak Structure Difference: 71.4 / 100 — Strong**;
- EBU LRA change: effectively **0.00 LU**;
- **Alignment: Reliable**.

The DR meter is measuring a real change in peak/RMS or crest structure, but the
higher DR value does **not** mean that the previously lost loudness dynamics have
been restored. A higher DR value from a vinyl or needledrop source therefore
cannot, by itself, prove that a more dynamic master was used.

The file name uses “Vinyl Remaster” as a short demo label. This is **not an actual
vinyl release or a complete physical vinyl-cutting/playback model**; it is a
controlled signal-processing simulation for demonstrating the measurement
problem.

### 3. Similar measured DR with different loudness dynamics

🎧 **Listen / download:**
[Reference MP3](examples/Eternal%20Desert%20-%20Reference.mp3) ·
[Vinyl-like transfer simulation](examples/Eternal%20Desert%20-%20Loudness%20War%20%28Vinyl%20Remaster%29.mp3)

The third experiment compares the original Reference directly with that same
vinyl-like transfer. Both versions measure **DR 10.4**, but their aligned
Short-Term loudness dynamics are clearly different.

![Similar measured DR with different loudness dynamics](assets/screenshots/dynamics-comparison-equal-dr.png)

MasVis for Windows reports:

- **Measured DR: 10.4 vs 10.4 — essentially equal**;
- **Loudness Dynamics Similarity: 62.9 / 100 — Moderate**;
- **Loudness Curve Similarity: 95.51%**;
- **Loudness Dynamics Advantage: Strong — Version A**;
- **Level Difference: Version B is 0.86 dB louder**;
- **Peak Structure Difference: 56.7 / 100 — Moderate**;
- **EBU LRA change: -3.95 LU in Version B**;
- **Alignment: Reliable**.

This is the complementary case: essentially equal measured DR values do not
necessarily imply equal loudness dynamics. Here the Reference retains a
substantially wider aligned Short-Term loudness span even though both versions
receive the same TT-style DR value.

All three experiments are practical validation examples, not proof that the
program can reconstruct mastering history. MasVis for Windows reports what the
measured signals support and keeps uncertainty visible when they do not support a
reliable conclusion.
## Highlights

- Native Windows interface with multiple report tabs, drag & drop and Advanced
  Open.
- Detailed MasVis reports with waveform, spectrum, crest factor, histogram,
  Peak-vs-RMS, EBU R128 loudness and TT-style DR information.
- Explainable **Dynamics Assessment** for single tracks.
- Same-content **Dynamics Comparison** with reliable-alignment gating,
  loudness-level matching and separate loudness/peak interpretation.
- **Play** button that sends the current original file to the default audio
  player configured in Windows. MasVis itself remains analysis-only.
- Side-by-side visual comparison with synchronized zoom and animated GIF export.
- Light/Dark application theme plus Light/Dark report presentation.
- Save and Save All with per-export format and resolution selection.
- High-resolution raster export to PNG, JPEG, WebP and TIFF, plus raster-backed
  SVG, PDF and EPS containers.
- Remembered open/export locations for a more natural Windows workflow.
- Built-in Help and Glossary covering both the classic report and the newer
  dynamics features in end-user language.
- FFmpeg/ffprobe decoding using a fixed, verified FFmpeg 9.0.1 Essentials build
  bundled with the portable Windows release.
- Bounded-memory True Peak processing that preserves validated results while
  greatly reducing temporary memory use on eligible input.

## What MasVis for Windows does not claim

MasVis for Windows is an analysis tool, not an automatic mastering judge.

It does **not**:

- rate whether a song sounds good or bad;
- prove which release came first or reconstruct mastering ancestry;
- treat a higher DR value as automatically better;
- treat vinyl/needledrop DR as proof of greater musical dynamics;
- use its 0-100 dynamics scores as statistical probabilities;
- contain its own audio player.

Use the measurements as evidence and context — then use your ears for preference.

## Supported audio files

The Windows interface currently accepts these extensions:

`WAV`, `FLAC`, `MP3`, `M4A`, `OGG`, `OPUS`, `AAC`, `AC3`, `AIFF`, `AIF`, `AMR`,
`ALAC`, `PCM`, `WMA`, `APE`

Actual decoding is performed by FFmpeg. A file still has to contain a stream
that the validated FFmpeg build can decode.

## Download and run

The public Windows release is available as a normal **Setup installer** and as a
**portable 64-bit ZIP**. Both contain the same validated MasVis for Windows
runtime and the exact bundled FFmpeg/ffprobe build.

### Setup installer — recommended for most users

1. Download `MasVis-for-Windows-1.1.0-Setup.exe` from the Releases page.
2. Run the installer.
3. Start **MasVis for Windows** from the Start menu or the optional desktop
   shortcut.

The installer places the application under Program Files, creates a normal
Windows uninstall entry and can update an existing MasVis for Windows
installation in place in future releases. It does **not** register MasVis as the
default application for audio files.

The current installer is not code-signed, so Windows may identify the publisher
as unknown when the downloaded Setup is launched.

### Portable ZIP

Prefer not to install anything? Download `MasVis-for-Windows-1.1.0-win64.zip`,
extract it to a normal folder and run `MasVis-for-Windows.exe`.

Python, PySide6/Qt, NumPy, SciPy, Matplotlib and the other tested runtime
dependencies are included in both distributions. The exact validated **Gyan
FFmpeg 9.0.1 Essentials** `ffmpeg.exe` and `ffprobe.exe` binaries are bundled as
well, so no separate FFmpeg installation or PATH configuration is required.

The tested release target is **Windows 11 x64**.

## Running from source

### Requirements

- Windows 11 x64 is the current development/test baseline.
- Python 3.11 or newer; current pinned Windows packaging baseline: Python 3.14.7.
- FFmpeg and ffprobe on `PATH`, or verified local copies under `vendor/ffmpeg/`.

Python dependencies are pinned in `requirements.txt`. Source runs prefer
verified binaries under `vendor/ffmpeg/` when present and otherwise fall back to
`PATH`. Packaged builds use only the verified FFmpeg binaries bundled with the
application and deliberately do not fall back to an arbitrary system FFmpeg.

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
python .\app.py
```

## Project lineage

MasVis for Windows would not exist without the work that came before it:

`MasVis -> PyMasVis -> MasVisGtk -> MasVis for Windows`

- **MasVisGtk** — ITProjects — direct upstream project and analysis/UI basis.
- **PyMasVis** — Joakim Fors — Python reimplementation of the original MasVis.
- **MasVis** — original project/research lineage.

This repository is an independent derivative/fork of MasVisGtk and links back
to the upstream project explicitly. MasVis for Windows is developed
independently and is **not an official MasVisGtk release**.

## Credits

Project direction, feature design, testing, and release decisions: **adventureFAN**.  
Most implementation, debugging, and technical documentation: developed collaboratively with **ChatGPT**.

## License and third-party software

MasVis for Windows is distributed under the **GNU General Public License,
version 3 or (at your option) any later version** (`GPL-3.0-or-later`). See
[`LICENSE`](LICENSE).

Reused or modified upstream source retains its original copyright notices. The
Windows fork's first-party modifications are Copyright (C) 2026 adventureFAN.

Packaged releases also contain third-party runtime components under their own
licenses, including Qt for Python/PySide6 and the validated GPLv3 Gyan FFmpeg
9.0.1 Essentials build. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
for attribution, exact build identity and source-access information.

## Repository

- Project: https://github.com/adventureFAN/MasVis-for-Windows
- Upstream: https://github.com/itprojects/MasVisGtk
