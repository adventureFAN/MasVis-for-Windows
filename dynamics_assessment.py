# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Explainable single-file dynamics / level-maximisation assessment.

This module is deliberately separate from the MasVis analysis core. It turns
already-computed MasVis measurements into a deterministic 0..100 evidence
index. The score is NOT a statistical probability, audio-quality rating or
claim about source/mastering ancestry.

Version 1.0 freezes the Research 0.3 calibration after mixed calibration and
held-out real-world corpora. Short-term PLR and allpass crest recovery remain
corroborative: strong local/phase-derived signatures are attenuated when the
current waveform simultaneously retains very generous whole-track PLR.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


ASSESSMENT_VERSION = "1.0"
ASSESSMENT_INDEX_NAME = "Level Maximization Evidence"


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    value: float
    max_points: float
    points: float
    interpretation: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class AssessmentResult:
    version: str
    index_name: str
    score: float
    label: str
    confidence: str
    summary: str
    metrics: dict[str, Any]
    components: list[dict[str, Any]]
    evidence: list[str]
    counter_evidence: list[str]
    cautions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_array(value: Any) -> np.ndarray:
    arr = np.asarray(value, dtype=float).reshape(-1)
    return arr[np.isfinite(arr)]


def _scalar(value: Any, default: float = float("nan")) -> float:
    arr = _finite_array(value)
    if arr.size == 0:
        return default
    return float(arr[0])


def _piecewise(value: float, points: list[tuple[float, float]]) -> float:
    """Linear interpolation over explicit (metric, score) calibration points."""
    if not np.isfinite(value):
        return 0.0
    xs = np.asarray([p[0] for p in points], dtype=float)
    ys = np.asarray([p[1] for p in points], dtype=float)
    return float(np.interp(value, xs, ys))


def _label(score: float) -> str:
    if score < 20:
        return "Low"
    if score < 40:
        return "Mild"
    if score < 60:
        return "Moderate"
    if score < 80:
        return "High"
    return "Very High"


def _strength(points: float, max_points: float) -> str:
    if max_points <= 0:
        return "None"
    ratio = points / max_points
    if ratio < 0.2:
        return "Low"
    if ratio < 0.45:
        return "Mild"
    if ratio < 0.7:
        return "Moderate"
    if ratio < 0.9:
        return "Strong"
    return "Very strong"


def _allpass_recovery(analysis: dict[str, Any]) -> tuple[float, float, list[float]]:
    crest = _finite_array(analysis.get("crest_db", []))
    ap = np.asarray(analysis.get("ap_crest", []), dtype=float)
    if crest.size == 0 or ap.ndim != 2 or ap.shape[1] != crest.size:
        return float("nan"), float("nan"), []

    channel_recovery = np.nanmax(ap, axis=0) - crest
    channel_recovery = channel_recovery[np.isfinite(channel_recovery)]
    if channel_recovery.size == 0:
        return float("nan"), float("nan"), []

    return (
        float(np.median(channel_recovery)),
        float(np.max(channel_recovery)),
        [float(v) for v in channel_recovery],
    )


def _loud_section_crest(analysis: dict[str, Any]) -> float:
    rms = np.asarray(analysis.get("rms_1s_dbfs", []), dtype=float)
    crest = np.asarray(analysis.get("crest_1s_db", []), dtype=float)
    if rms.ndim != 2 or crest.shape != rms.shape or rms.shape[1] == 0:
        return float("nan")

    per_channel: list[float] = []
    for channel in range(rms.shape[0]):
        valid = np.isfinite(rms[channel]) & np.isfinite(crest[channel])
        if not np.any(valid):
            continue
        r = rms[channel][valid]
        c = crest[channel][valid]
        # Use the loudest 20 % of one-second windows. These are the regions
        # where a mastering limiter is most likely to reveal itself.
        threshold = float(np.percentile(r, 80.0))
        selected = c[r >= threshold]
        if selected.size:
            per_channel.append(float(np.median(selected)))

    if not per_channel:
        return float("nan")
    return float(np.median(per_channel))


def _short_term_plr(analysis: dict[str, Any]) -> tuple[float, float, float]:
    values = _finite_array(analysis.get("stplr_lu", []))
    if values.size == 0:
        return float("nan"), float("nan"), float("nan")
    return (
        float(np.percentile(values, 20.0)),
        float(np.median(values)),
        float(np.percentile(values, 80.0)),
    )




def _allpass_points(
    ap_recovery_db: float,
    overall_plr: float,
) -> tuple[float, float, float]:
    """Return (final points, raw points, corroboration factor), max 35.

    MasVis allpass crest recovery is deliberately retained as the strongest
    individual indicator, but Research 0.2 exposed an ambiguity case where a
    very large recovery coexisted with generous whole-track PLR. In that
    situation the recovery may still be meaningful, but attributing nearly
    the full 35 points to *current-waveform* level maximisation is too strong.

    0.3 therefore attenuates only the score contribution as PLR becomes more
    generous. The raw recovery value is preserved and reported so unusual
    phase/peak behaviour remains visible. A non-zero floor is intentional:
    strong allpass recovery is not discarded merely because corroboration is
    weak.
    """
    raw_points = _piecewise(
        ap_recovery_db,
        [(0.0, 0.0), (0.5, 2.0), (1.0, 5.0), (2.0, 12.0),
         (3.0, 20.0), (4.0, 28.0), (5.0, 33.0), (6.0, 35.0)],
    )
    corroboration = _piecewise(
        overall_plr,
        [(4.0, 1.0), (10.0, 1.0), (11.0, 0.95), (12.0, 0.85),
         (13.0, 0.72), (14.0, 0.58), (15.0, 0.48), (16.0, 0.40),
         (17.0, 0.35), (20.0, 0.35)],
    )
    final_points = raw_points * corroboration
    return float(final_points), float(raw_points), float(corroboration)

def _short_term_density_points(
    stplr_p20: float,
    stplr_median: float,
    overall_plr: float,
) -> tuple[float, float, float]:
    """Return (final points, raw points, corroboration factor), max 15.

    Research 0.1 scored the 20th percentile directly. That correctly detects
    persistently dense masters, but it can overstate a programme that has only
    some dense/loud passages while retaining very generous overall headroom.

    0.2 therefore:
      * gives more weight to the median than the lower fifth of ST-PLR;
      * treats the result as corroborative evidence and attenuates it when the
        whole-track PLR is generous.

    This is deliberately deterministic and explicit, not a trained model.
    """
    p20_points = _piecewise(
        stplr_p20,
        [(3.0, 15.0), (6.0, 14.0), (8.0, 11.0), (10.0, 6.0),
         (12.0, 2.0), (14.0, 0.0), (20.0, 0.0)],
    )
    median_points = _piecewise(
        stplr_median,
        [(3.0, 15.0), (6.0, 14.0), (8.0, 11.0), (10.0, 7.0),
         (12.0, 3.0), (14.0, 0.0), (20.0, 0.0)],
    )
    raw_points = 0.35 * p20_points + 0.65 * median_points

    corroboration = _piecewise(
        overall_plr,
        [(4.0, 1.0), (9.0, 1.0), (11.0, 0.90), (13.0, 0.55),
         (15.0, 0.20), (17.0, 0.0), (20.0, 0.0)],
    )
    final_points = raw_points * corroboration
    return float(final_points), float(raw_points), float(corroboration)


def assess_metrics(metrics: dict[str, Any]) -> AssessmentResult:
    """Score a pre-derived metric dictionary.

    This function also keeps the calibration/replay tools useful without
    decoding/analyzing the same audio again. ``assess_dynamics`` is the normal
    application entry point that derives these metrics from a MasVis analysis
    dictionary.
    """
    integrated_lufs = float(metrics.get("integrated_lufs", float("nan")))
    lra = float(metrics.get("lra_lu", float("nan")))
    plr = float(metrics.get("plr_lu", float("nan")))
    dr = float(metrics.get("dr", -1))
    crest_total = float(metrics.get("crest_total_db", float("nan")))
    true_peak = float(metrics.get("true_peak_dbtp", float("nan")))
    ap_median = float(metrics.get("allpass_recovery_median_db", float("nan")))
    ap_max = float(metrics.get("allpass_recovery_max_db", float("nan")))
    ap_channels = [float(v) for v in metrics.get("allpass_recovery_channels_db", [])]
    stplr_p20 = float(metrics.get("short_term_plr_p20_lu", float("nan")))
    stplr_median = float(metrics.get("short_term_plr_median_lu", float("nan")))
    stplr_p80 = float(metrics.get("short_term_plr_p80_lu", float("nan")))
    loud_crest = float(metrics.get("loud_section_crest_median_db", float("nan")))
    duration = float(metrics.get("duration_seconds", 0.0) or 0.0)
    channels = int(metrics.get("channels", 0) or 0)
    stl_count = int(metrics.get("short_term_windows", 0) or 0)

    allpass_points, allpass_raw, allpass_corroboration = _allpass_points(
        ap_median, plr
    )
    short_points, short_raw, short_corroboration = _short_term_density_points(
        stplr_p20, stplr_median, plr
    )

    component_specs = [
        (
            "allpass_crest_recovery",
            ap_median,
            35.0,
            allpass_points,
            {
                "raw_points_before_corroboration": allpass_raw,
                "overall_plr_corroboration_factor": allpass_corroboration,
            },
        ),
        (
            "peak_to_loudness_ratio",
            plr,
            25.0,
            _piecewise(plr, [(4.0, 25.0), (6.0, 25.0), (7.0, 23.0), (9.0, 18.0), (11.0, 10.0), (13.0, 4.0), (15.0, 0.0), (20.0, 0.0)]),
            None,
        ),
        (
            "short_term_density",
            stplr_median,
            15.0,
            short_points,
            {
                "p20_lu": stplr_p20,
                "median_lu": stplr_median,
                "p80_lu": stplr_p80,
                "raw_points_before_corroboration": short_raw,
                "overall_plr_corroboration_factor": short_corroboration,
            },
        ),
        (
            "loud_section_crest",
            loud_crest,
            15.0,
            _piecewise(loud_crest, [(3.0, 15.0), (6.0, 14.0), (8.0, 11.0), (10.0, 7.0), (12.0, 3.0), (14.0, 0.0), (20.0, 0.0)]),
            None,
        ),
        (
            "integrated_loudness",
            integrated_lufs,
            10.0,
            _piecewise(integrated_lufs, [(-24.0, 0.0), (-18.0, 0.0), (-14.0, 2.0), (-12.0, 4.0), (-10.0, 7.0), (-8.0, 9.0), (-6.0, 10.0), (-3.0, 10.0)]),
            None,
        ),
    ]

    components: list[ScoreComponent] = []
    for name, value, max_points, points, details in component_specs:
        points = max(0.0, min(float(max_points), float(points)))
        components.append(
            ScoreComponent(
                name=name,
                value=float(value),
                max_points=float(max_points),
                points=points,
                interpretation=_strength(points, max_points),
                details=details,
            )
        )

    score = round(sum(c.points for c in components), 1)

    if duration < 15.0 or stl_count < 5:
        confidence = "Low"
    elif duration < 60.0 or stl_count < 20:
        confidence = "Medium"
    else:
        confidence = "High"

    evidence: list[str] = []
    counter: list[str] = []
    cautions: list[str] = []

    if np.isfinite(ap_median):
        if ap_median >= 4.0 and allpass_corroboration >= 0.80:
            evidence.append("Large allpass crest-factor recovery, corroborated by limited overall PLR, suggests substantial crest-factor loss from level maximisation.")
        elif ap_median >= 2.0 and allpass_corroboration >= 0.70:
            evidence.append("Allpass crest-factor recovery provides moderate evidence of level maximisation and is reasonably corroborated by whole-track PLR.")
        elif ap_median >= 4.0 and allpass_corroboration <= 0.55:
            counter.append("Large allpass crest-factor recovery is present, but generous overall PLR weakens attributing it primarily to current-waveform level maximisation; unusual phase/peak structure remains a plausible contributor.")
        elif ap_median >= 2.0 and allpass_corroboration < 0.70:
            counter.append("Allpass crest-factor recovery is noticeable, but generous overall PLR provides limited corroboration for level maximisation as its main cause.")
        elif ap_median <= 1.0:
            counter.append("Allpass crest-factor recovery is small, providing little direct evidence of destructive level maximisation in this waveform.")

    if np.isfinite(plr):
        if plr <= 8.0:
            evidence.append("PLR is very low, indicating little peak headroom relative to integrated loudness.")
        elif plr <= 10.0:
            evidence.append("PLR is low and consistent with a dense or strongly limited master.")
        elif plr >= 13.0:
            counter.append("PLR leaves comparatively generous peak headroom.")

    if np.isfinite(stplr_p20) and np.isfinite(stplr_median):
        if short_points >= 9.0:
            evidence.append("Short-term PLR is persistently low and is corroborated by limited whole-track peak headroom.")
        elif short_raw >= 8.0 and short_corroboration <= 0.35:
            counter.append("Some loud short-term windows are dense, but generous overall PLR makes them weak evidence of whole-track level maximisation.")
        elif short_points <= 2.0 and stplr_median >= 12.0:
            counter.append("Short-term PLR retains substantial headroom through most measured windows.")

    if np.isfinite(loud_crest):
        if loud_crest <= 8.0:
            evidence.append("The loudest one-second sections have low crest factor, consistent with restricted transients.")
        elif loud_crest >= 12.0:
            counter.append("The loudest sections retain comparatively strong crest factor.")

    if np.isfinite(integrated_lufs):
        if integrated_lufs >= -9.0:
            evidence.append("Integrated loudness is extremely high; this strengthens other limiting evidence but is not decisive by itself.")
        elif integrated_lufs <= -15.0:
            counter.append("Integrated loudness is comparatively low, reducing evidence of loudness-driven level maximisation.")

    if not evidence and score < 40.0:
        counter.append("No individual metric provides strong direct evidence of aggressive level maximisation; the remaining score is an accumulation of mild waveform signatures.")

    if duration < 30.0:
        cautions.append("Short programme duration reduces the reliability of distribution-based metrics such as LRA and short-term PLR.")
    if channels > 2:
        cautions.append("Multichannel assessment is exploratory in version 1.0; calibration is currently focused on mono/stereo music masters.")
    cautions.append("This index describes direct level-maximisation signatures in the current waveform; it does not identify the ancestry or earlier mastering history of the source.")
    cautions.append("A low score for a vinyl/captured/processed version does not prove that its source master was uncompressed; alternate-master questions require a direct comparison.")
    cautions.append("The score is a deterministic evidence index, not a statistical probability and not an audio-quality judgement.")
    cautions.append("Genre, artistic intent, source medium and earlier analogue processing can affect these measurements.")

    clean_metrics = dict(metrics)
    clean_metrics["allpass_recovery_raw_points"] = allpass_raw
    clean_metrics["allpass_plr_corroboration_factor"] = allpass_corroboration
    clean_metrics["short_term_density_raw_points"] = short_raw
    clean_metrics["short_term_plr_corroboration_factor"] = short_corroboration

    label = _label(score)
    summaries = {
        "Low": "Little direct evidence of aggressive level maximization is present in this waveform.",
        "Mild": "Some level-maximization signatures are present, but the overall evidence is limited.",
        "Moderate": "Several level-maximization signatures are present, but the evidence is mixed.",
        "High": "Strong combined evidence of level maximization is present in this waveform.",
        "Very High": "Very strong combined evidence of aggressive level maximization is present in this waveform.",
    }

    return AssessmentResult(
        version=ASSESSMENT_VERSION,
        index_name=ASSESSMENT_INDEX_NAME,
        score=score,
        label=label,
        confidence=confidence,
        summary=summaries[label],
        metrics=clean_metrics,
        components=[asdict(c) for c in components],
        evidence=evidence,
        counter_evidence=counter,
        cautions=cautions,
    )


def assess_dynamics(track: dict[str, Any], analysis: dict[str, Any]) -> AssessmentResult:
    """Create the explainable single-file assessment.

    The score expresses accumulated direct evidence of loudness-oriented
    dynamic reduction / level maximisation in the current waveform. It is not
    a probability, quality judgement, genre-aware mastering verdict, or claim
    about the source/mastering ancestry of an alternate medium.
    """

    integrated_lufs = _scalar(analysis.get("l_kg"))
    lra = _scalar(analysis.get("lra"))
    plr = _scalar(analysis.get("plr_lu"))
    dr = float(analysis.get("dr", -1))
    crest_total = _scalar(analysis.get("crest_total_db"))
    true_peak_values = _finite_array(analysis.get("true_peak_dbtp", []))
    true_peak = float(np.max(true_peak_values)) if true_peak_values.size else float("nan")

    ap_median, ap_max, ap_channels = _allpass_recovery(analysis)
    stplr_p20, stplr_median, stplr_p80 = _short_term_plr(analysis)
    loud_crest = _loud_section_crest(analysis)

    metrics = {
        "integrated_lufs": integrated_lufs,
        "lra_lu": lra,
        "plr_lu": plr,
        "dr": dr,
        "crest_total_db": crest_total,
        "true_peak_dbtp": true_peak,
        "allpass_recovery_median_db": ap_median,
        "allpass_recovery_max_db": ap_max,
        "allpass_recovery_channels_db": ap_channels,
        "short_term_plr_p20_lu": stplr_p20,
        "short_term_plr_median_lu": stplr_median,
        "short_term_plr_p80_lu": stplr_p80,
        "loud_section_crest_median_db": loud_crest,
        "duration_seconds": float(track.get("duration", 0.0) or 0.0),
        "channels": int(track.get("channels", 0) or 0),
        "short_term_windows": int(_finite_array(analysis.get("stl", [])).size),
    }
    return assess_metrics(metrics)
