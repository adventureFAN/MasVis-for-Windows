# Dynamics Comparison v1.0

Date: 2026-08-21

Dynamics Comparison is the two-file interpretation layer in MasVis for
Windows. It compares two versions of substantially the same musical material
and explicitly separates peak-based measured DR from aligned Short-Term loudness
dynamics.

## Core product rule

Always show both exact measured MasVis/TT-style DR values and identify the file
with the higher measured DR. Never suppress or redefine that measurement.
Independently determine whether the aligned Short-Term loudness development shows
a corresponding dynamics advantage.

A pure gain change cannot raise DR, PLR or crest factor. Level difference is
therefore reported separately from peak-structure changes.

## Alignment / rejection gate

The comparison derives 100 ms EBU R128 momentary and Short-Term loudness series
with FFmpeg, estimates a global offset, and refines a linear timing model so
small playback-speed differences can be represented. A user-facing verdict is
issued only for `Reliable` alignment. Anything weaker is `Inconclusive`.

## Loudness Curve Similarity

The displayed percentage is the actual Pearson correlation of the aligned
Short-Term loudness trajectories. It is a direct mathematical similarity
measurement, not a probability.

## Loudness Dynamics Similarity: 0..100

This is a deterministic, explainable score and not a statistical probability.
Frozen v1 weighting:

- 55% trajectory-correlation component;
- 30% post-level-match residual-similarity component;
- 15% robust Short-Term loudness-span similarity component.

Labels:

- under 60: Low
- 60..79.9: Moderate
- 80..89.9: High
- 90..96.9: Very High
- 97..100: Extremely High

The score is intentionally scoped to the aligned Short-Term loudness
development. It does **not** claim that transient, crest or peak dynamics are
identical; those are described separately by Peak Structure Difference.

## Loudness Dynamics Advantage

Direction is A, B, None, Mixed or Inconclusive. TT DR and PLR are deliberately
excluded from this direction decision to avoid circularly treating peak-based
headroom as proof of loudness dynamics.

Evidence:

- 70% aligned robust Short-Term loudness-span delta;
- 30% EBU LRA delta.

Magnitude bands on the combined delta:

- under 0.60 dB: None detected
- 0.60..1.49 dB: Slight
- 1.50..2.99 dB: Moderate
- 3.00 dB or more: Strong

Materially opposing Short-Term and LRA directions are exposed as Mixed rather
than averaged into a deceptively clean winner.

## Peak Structure Difference

A separate 0..100 score describes how strongly peak/crest structure differs
after time alignment and loudness-level matching. It uses robust median and p90
peak-lift / crest-delta magnitudes. This is descriptive; it does not claim that
one version sounds better.

## Main conclusion classes

- Primarily a level shift
- Higher measured DR, but little loudness-dynamics advantage
- Higher measured DR is not corroborated by loudness dynamics
- Higher measured DR is corroborated
- Measured DR and loudness dynamics disagree
- Mixed evidence / mixed loudness-dynamics evidence
- Loudness dynamics differ despite similar measured DR
- Essentially the same loudness dynamics
- Inconclusive / Uncertain

## Validation basis

The v1 freeze followed ten engineering comparison cases: three known reference
pairs, six new real-world pairs and one deliberate wrong-song negative control.
The set contains examples of much higher DR with almost unchanged loudness
trajectory, a directional corroborated DR advantage, a DR-vs-loudness-dynamics
conflict, vinyl/capture-like peak regeneration and Inconclusive mismatch.

A separate synthetic -6 dB pure-gain test yielded equal DR/PLR, 100.0 Loudness Dynamics
Similarity, 0.0 Peak Structure Difference and `Primarily a level shift`.

This validation supports a practical v1 feature. It is not a statistical model
trained on a labelled population and does not establish universal scientific
classification accuracy.
