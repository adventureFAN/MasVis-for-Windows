# Eternal Desert — reproducible demo material

This folder contains three controlled versions of **Eternal Desert** used by the
Dynamics Comparison examples in the MasVis for Windows README. They are included
so users can listen to the material and reproduce both comparison cases
themselves.

## Files

### `Eternal Desert - Reference.mp3`

The reference version of *Eternal Desert*.

- Duration: about 4:52.7
- Stereo, 48 kHz MP3
- Approximate EBU R128 measurement with the validated analysis path:
  **-14.3 LUFS-I**, **8.4 LU LRA**, **-1.1 dBTP**

### `Eternal Desert - Loudness War.mp3`

A deliberately louder and denser derivative of the reference file, created as a
controlled **Loudness War / level-maximization stress test**.

- Same musical content and duration
- Stereo, 48 kHz MP3
- Approximate EBU R128 measurement with the validated analysis path:
  **-7.9 LUFS-I**, **4.5 LU LRA**, **+1.0 dBTP**

Compared with the Reference, MasVis for Windows 1.1.0 reports **DR 10.4 vs 6.5**
and an aligned level difference of about **+6.70 dB** for the Loudness War
version. In this case the lower DR value coincides with a real reduction in the
aligned Short-Term loudness dynamics.

### `Eternal Desert - Loudness War (Vinyl Remaster).mp3`

A deliberately simplified **vinyl-like transfer simulation** made from the
already compressed Loudness War master. Despite the filename used for the demo,
this is **not an actual vinyl master, pressing or needledrop**, and it is not a
complete physical model of vinyl cutting and playback.

The test processing intentionally changes signal and peak geometry without using
expansion or attempting to restore the dynamics removed by the Loudness War
master. The chain used in Audacity/Nyquist includes:

- Mid/Side processing with reduced low-frequency Side content;
- gentle high-pass and low-pass filtering;
- two all-pass stages for controlled phase rotation;
- a small amount of stereo crosstalk;
- final peak normalization, with no dynamic expansion or limiting used to
  recreate the lost loudness movement.

The supplied MP3 is about 4:52.7 long, stereo at 48 kHz. A direct FFmpeg EBU R128
check of this exact file measures approximately **-13.9 LUFS-I**, **4.5 LU LRA**
and **-1.0 dBTP**.

Compared directly with `Eternal Desert - Loudness War.mp3`, MasVis for Windows
1.1.0 reports:

- **Measured DR: 6.5 vs 10.2** (+3.7 for the vinyl-like file);
- **Loudness Dynamics Similarity: 99.3 / 100 — Extremely High**;
- **Loudness Curve Similarity: 99.77%**;
- **Loudness Dynamics Advantage: None detected**;
- **Level Difference: Version B is 5.97 dB quieter**;
- **Peak Structure Difference: 71.6 / 100 — Strong**;
- **EBU LRA change: effectively 0.00 LU**;
- **Alignment: Reliable**.

This is the deliberately counter-intuitive example: the measured DR rises from
**6.5 to 10.2**, almost matching the Reference's **10.4**, even though the
aligned loudness dynamics remain essentially unchanged. The extra DR comes from
changed peak/crest structure, not from restoring the compressed musical loudness
development.

## How to try the examples

### Experiment 1 — Reference vs Loudness War

1. Open `Eternal Desert - Reference.mp3` and `Eternal Desert - Loudness War.mp3`.
2. Run **Dynamics Comparison**.
3. Observe the lower DR together with the genuine reduction in aligned loudness
   dynamics.

### Experiment 2 — Loudness War vs vinyl-like transfer

1. Open `Eternal Desert - Loudness War.mp3` and
   `Eternal Desert - Loudness War (Vinyl Remaster).mp3`.
2. Run **Dynamics Comparison**.
3. Observe that DR rises strongly while LDS remains extremely high, no Loudness
   Dynamics Advantage is detected, and the strongest difference is instead in
   peak structure.

The examples are not intended to declare one version “good” and another “bad”.
They demonstrate why DR is useful evidence but cannot, on its own, describe every
kind of dynamic change or prove that a vinyl/needledrop source used a different
master.

## Creation and licensing

*Eternal Desert* is an **AI-assisted song created with Suno**, with **lyrics and
creative prompting by adventureFAN**.

The reference song was originally generated while using Suno's Free plan. Suno
Support subsequently provided adventureFAN with **written permission extending
the Pro/commercial terms to this specific song** and explicitly confirmed that
the audio may be included publicly with this open-source project, made
downloadable, and used as demonstration material. The support correspondence is
retained privately by the project author as the licensing record.

The Loudness War and vinyl-like files are deliberately modified derivatives of
that cleared reference material, prepared specifically for these demonstrations.

**These MP3 files are not covered by the GPL-3.0-or-later license that applies to
MasVis for Windows source code.** They are provided as example/test material for
this project. No broader license for unrelated redistribution, relicensing or
commercial exploitation is granted by this repository.
