# MasVis for Windows 1.1.1 — release notes

## Focused visual-semantics patch

MasVis for Windows 1.1.1 is a deliberately small patch release. It changes the
visual treatment of the **Dynamics Assessment** score and **Loudness Dynamics
Similarity (LDS)** so that measurement strength is not presented with an
evaluative traffic-light palette.

## Change

- Replaced the Dynamics Assessment score badge's green/brown/red progression
  with a value-neutral monochromatic blue progression. Higher scores still have
  stronger visual intensity, but the color no longer suggests a sound-quality
  grade.
- Replaced the LDS badge's traffic-light-style palette with the same
  value-neutral blue progression. Higher LDS values still have stronger visual
  intensity, but the color no longer implies that higher similarity is
  inherently better.
- The blue steps were made deliberately more distinct while keeping white badge
  text readable in both Light and Dark application themes.
- All existing Assessment and LDS labels and thresholds remain unchanged.
- `Inconclusive` remains neutral gray.

## Analysis compatibility

There are **no changes** to Dynamics Assessment or Dynamics Comparison formulas,
weights, thresholds, alignment, level matching, Loudness Dynamics Advantage,
Peak Structure Difference or any classic MasVis measurement. Existing 1.1.0
analysis results therefore remain directly comparable with 1.1.1.

## Distribution

The release continues to use the same previously validated self-contained Windows
packaging baseline and pinned Gyan FFmpeg 9.0.1 Essentials runtime. The Setup
installer retains the same stable Inno Setup AppId and is designed to update an
existing MasVis for Windows installation in place.

---

# MasVis for Windows 1.1.0 — release notes

## Feature and maintenance release

MasVis for Windows 1.1.0 combines the first post-release bug fixes with a
small export/workflow polish pass. It does not change the frozen Dynamics
Assessment v1 scoring model or the Loudness Dynamics Similarity weighting used
by Dynamics Comparison v1.

## Fixes

- Fixed the Processing dialog **Cancel** action so the cancellation request is
  delivered immediately instead of waiting behind the busy worker thread.
  FFmpeg/ffprobe decoding can now be terminated cooperatively while it is
  running, and MasVis analysis checks cancellation between its major calculation
  steps. An already running NumPy/SciPy calculation step or report render may
  still need to finish before processing stops.
- Fixed **Peak Structure Difference** p90 magnitude handling so the difference
  score is symmetric when Version A and Version B are swapped.
- Made the displayed **Level Difference** use the same aligned Momentary-loudness
  level match that is used for peak-structure comparison.
- Fixed the legacy `dynamic_range()` error fallback so it always returns the
  two-value shape expected by its caller instead of raising a secondary unpacking
  error.
- Closed the temporary legacy Overview Matplotlib buffer figure after rendering.
- Selected Matplotlib's non-interactive `Agg` backend before importing `pyplot`.

## Workflow and export polish

- Moved **Preferences** to the right-side toolbar position directly beside Help.
- Removed the extra modal confirmation after a user-initiated processing cancel;
  the Processing dialog now simply closes once cancellation has completed.
- Save, Save All and animated GIF export now choose their export-specific options
  directly in their respective dialogs instead of placing those controls in
  Preferences.
- Renamed export **Quality** to **Resolution** so the setting reflects what it
  primarily controls. Report export resolutions are now:
  - Standard: 606 px wide
  - High: 1212 px wide
  - Very High: 1818 px wide
  Exports never upscale beyond the already-rendered source report.
- GIF export uses the same explicit **Resolution** wording while retaining its
  existing 606 / 810 / 1080 px width choices and frame-duration control.
- Save and Save All share and remember the last-used export folder. On a fresh
  settings profile they start in the current Windows user's home folder.
- Open Files and Advanced Open remember the last-used source folder, also falling
  back to the current user's home folder on first use.
- GIF export remembers its last-used destination folder.
- Removed success confirmation popups after **Save All** and **GIF Export**;
  successful user-initiated exports now complete without an extra modal dialog.
- Removed the **Compare** width setting from Preferences. Compare windows remember
  the last-used report width directly from their zoom controls and use it as the
  starting width for the next comparison.
- Detailed report footers now identify the actual host application as
  **MasVis for Windows 1.1.0** instead of retaining the upstream `MasVisGtk 6.1.0`
  renderer label. This is presentation-only; the upstream lineage remains credited
  in Help, About, README and third-party notices.
- Expanded the built-in **Glossary** with the loudness/dynamics terminology used
  by Dynamics Assessment and Dynamics Comparison, including LDS, Loudness Curve
  Similarity, Loudness Dynamics Advantage, Peak Structure Difference, alignment,
  level matching, dBFS/dBTP, compression/limiting/clipping and vinyl/needledrop
  interpretation cautions.
- Reviewed and rewrote the built-in Help as a compact end-user guide: clearer
  first-use workflow, more approachable report explanations, an explicit simple
  question for Dynamics Assessment and Dynamics Comparison, practical reading
  order for comparison results, clearer limits of the assessment features, and
  an explicit distinction between Report Quality and export Resolution.
- Added a **Play** action directly beside Save All for individual detailed report
  tabs. It does not add an audio player to MasVis: it hands the original analyzed
  file to the default audio application configured in Windows. The action is
  disabled when there is no individual file to play, and a clear message is shown
  when the source file is missing or Windows has no associated default application.

## Technical maintenance

- Dynamics Comparison now feeds its EBU R128 and peak/RMS metadata branches from
  one decoded FFmpeg input pass per file instead of decoding each file twice for
  the two trajectories. The branch filters and 100 ms measurements themselves
  are unchanged.
- Internal helper naming now consistently refers to **Loudness Dynamics
  Advantage**. The existing `musical_dynamics_advantage` result key is retained
  for stored Research 0.2 / Dynamics Comparison v1 compatibility.
- Dynamics Assessment v1 and Dynamics Comparison v1 scoring formulas, thresholds
  and weights remain unchanged.

## Settings compatibility

Existing 1.0.0 settings remain usable. The old internal `export_quality` and
`gif_quality` values are accepted as migration fallbacks and are replaced by the
clearer `export_resolution` / `gif_resolution` settings on subsequent saves.

## Distribution

The Windows release remains a self-contained portable x64 ZIP with the exact
validated Gyan FFmpeg 9.0.1 Essentials runtime bundled. No separate FFmpeg
installation, setup helper or PATH configuration is required.

## Lineage and license

MasVis for Windows is an independent Windows-native fork of MasVisGtk by
ITProjects. MasVisGtk builds on PyMasVis by Joakim Fors, a Python
reimplementation of the original MasVis. MasVis for Windows is distributed
under GPL-3.0-or-later; packaged third-party components retain their own
licenses and notices.

---

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
