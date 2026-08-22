# Eternal Desert — reproducible demo material

This folder contains the two audio files used by the **Dynamics Comparison**
example in the MasVis for Windows README and screenshots. They are included so
users can reproduce the comparison themselves.

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

In the MasVis for Windows 1.1.0 Dynamics Comparison test pair, the application
reports **DR 10.4 vs 6.5** and an aligned level difference of about **+6.70 dB**
for the Loudness War version. The aligned level difference is not the same metric
as the simple difference between the two integrated LUFS-I values.

## How to try the example

1. Open both MP3 files in MasVis for Windows.
2. Select the two detailed report tabs.
3. Run **Dynamics Comparison**.
4. Compare measured DR, Loudness Dynamics Similarity, Loudness Curve Similarity,
   Loudness Dynamics Advantage and Peak Structure Difference.

The point of the pair is not to declare one version "good" and the other "bad".
It is to show why a single DR number cannot describe every kind of dynamic
change.

## Creation and licensing

*Eternal Desert* is an **AI-assisted song created with Suno**, with **lyrics and
creative prompting by adventureFAN**.

The reference song was originally generated while using Suno's Free plan. Suno
Support subsequently provided adventureFAN with **written permission extending
the Pro/commercial terms to this specific song** and explicitly confirmed that
the audio may be included publicly with this open-source project, made
downloadable, and used as demonstration material. The support correspondence is
retained privately by the project author as the licensing record.

The Loudness War file is a deliberately modified derivative of that cleared
reference material, prepared specifically for this demonstration.

**These MP3 files are not covered by the GPL-3.0-or-later license that applies to
MasVis for Windows source code.** They are provided as example/test material for
this project. No broader license for unrelated redistribution, relicensing or
commercial exploitation is granted by this repository.
