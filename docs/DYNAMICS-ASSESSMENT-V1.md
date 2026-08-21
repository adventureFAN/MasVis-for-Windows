# Dynamics Assessment v1

Date: 2026-08-21

## Purpose

`Dynamics Assessment` is an explainable single-file interpretation layer for
MasVis for Windows. It summarizes several already-computed MasVis
measurements into a deterministic **Level Maximization Evidence** index from
0 to 100.

The index is **not a statistical probability**, an objective audio-quality
rating, a genre judgement, or a claim about source/mastering ancestry. It
answers a narrower question: how strongly does the **current waveform** show a
combination of measurable signatures associated with level maximization and
strong limiting?

## Frozen v1 score definition

The v1 formula is the Research 0.3 calibration, frozen after the initial,
broader and held-out mixed real-world corpora. Maximum score contributions:

- Allpass crest-factor recovery: 35 points.
  - Large recovery is retained as the strongest individual clue.
  - Its attributed score contribution is attenuated when whole-track PLR is
    very generous, because unusual phase/peak structure can also create a
    large allpass response.
- Peak-to-Loudness Ratio (PLR): 25 points.
- Short-term density: 15 points.
  - Uses ST-PLR p20 and median, weighted 35/65.
  - The contribution is corroborated/attenuated by whole-track PLR.
- Crest factor in the loudest 20% of one-second sections: 15 points.
- Integrated Loudness: 10 points.

TT-style DR and LRA are shown as context but do not directly add points.

Score bands:

- 0-19: Low
- 20-39: Mild
- 40-59: Moderate
- 60-79: High
- 80-100: Very High

## Calibration history

Research 0.1 established the first transparent five-component score and found
that short-term PLR could overreact to isolated dense sections in otherwise
high-headroom material.

Research 0.2 made short-term density corroborative with whole-track PLR. The
identified `Stairway To Heaven` ambiguity dropped from 16.5 to 4.3 while known
strong examples remained high.

Research 0.3 made allpass-recovery attribution corroborative with whole-track
PLR. This addressed high-allpass/high-PLR ambiguity without suppressing the
raw allpass measurement. Known severe cases remained effectively unchanged.

A subsequent blind/held-out run used 30 genuinely new tracks drawn from a wild
cross-genre mixture, including many highly ranked songs from Rolling Stone's
"500 Greatest Songs of All Time" list. The formula was **not changed after
that held-out run**. It continued to produce a broad distribution rather than
sorting mechanically by age, genre or TT DR. This is encouraging engineering
validation, not a scientific labelled-dataset validation.

## GUI integration

MasVis for Windows 1.0 computes the assessment immediately after the normal MasVis
analysis while the full analysis arrays are still available. Only the small
assessment result dictionary is stored in the result tab; full audio/analysis
arrays are still released as before.

The header button uses Microsoft's official Fluent UI System Icons
`Data Histogram 24 Regular` artwork and appears immediately to the right of
the DR badge for a detailed result tab:

`DR -> Dynamics Assessment -> Compare`

Overview tabs do not expose the single-file Assessment button.

The modal Assessment window displays:

- the 0..100 Level Maximization Evidence index and Low/Mild/Moderate/High/Very
  High label;
- measurement confidence (programme-length based, not statistical model
  confidence);
- deterministic summary text;
- positive evidence and counter-evidence/ambiguity;
- per-component score contribution;
- key measurements;
- limitations/cautions;
- `Copy Assessment` for clipboard export.

The Help dialog contains a dedicated `Dynamics Assessment` page explaining the
method, weights, labels and limitations in end-user language.

## Critical interpretation rule

A low single-file score on vinyl, captured or otherwise processed material
does **not** prove that the underlying source master was uncompressed. EQ,
filtering, phase changes and medium/capture effects can regenerate peaks and
change crest/DR measurements without restoring lost musical dynamics.

Determining whether an alternate version shows different aligned Short-Term
loudness dynamics requires the separate `Dynamics Comparison` analysis.
Single-file Assessment must never claim to reconstruct source/mastering history.

## Release status

The v1 assessment formula is frozen for the 1.0 release line. Do not retune it
merely to make individual favourite or famous tracks land in expected
categories. Any future calibration change should be versioned and revalidated
against both the calibration and held-out corpora.
