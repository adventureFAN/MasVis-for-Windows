# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Explainable two-file Dynamics Comparison v1.0.

The comparison aligns two versions of the same musical material, level-matches
the aligned loudness trajectories, and then keeps peak-based measurements
separate from Short-Term loudness dynamics.  The 0..100 Loudness Dynamics Similarity index
is an explainable engineering score, not a statistical probability.

The implementation deliberately uses compact FFmpeg-derived 100 ms series so
two full decoded tracks never need to remain in Python memory at once.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from dynamics_common import (
    aligned_values,
    estimate_global_lag,
    extract_audio_series,
    measure_masvis_dr,
    probe_basic,
    refine_linear_alignment,
    robust_series_stats,
)


COMPARE_VERSION = "1.0"


def _finite(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def _piecewise(value: float, points: list[tuple[float, float]]) -> float:
    if not np.isfinite(value):
        return 0.0
    xs = np.asarray([p[0] for p in points], dtype=float)
    ys = np.asarray([p[1] for p in points], dtype=float)
    return float(np.interp(value, xs, ys))


def _delta(metrics_a: dict[str, Any] | None, metrics_b: dict[str, Any] | None, key: str) -> float:
    if not metrics_a or not metrics_b:
        return float("nan")
    a = _finite(metrics_a.get(key))
    b = _finite(metrics_b.get(key))
    return b - a if np.isfinite(a) and np.isfinite(b) else float("nan")


def _alignment_quality(momentary: dict[str, float], alignment: dict[str, Any]) -> tuple[str, list[str]]:
    r = _finite(momentary.get("correlation"), -1.0)
    anchors = int(alignment.get("anchor_count", 0))
    anchor_r = _finite(alignment.get("anchor_median_correlation"), 0.0)
    speed = abs(_finite(alignment.get("speed_difference_percent"), 99.0))
    notes: list[str] = []

    if r >= 0.90 and anchors >= 4 and anchor_r >= 0.65 and speed <= 2.0:
        return "Reliable", notes
    if r >= 0.75 and anchors >= 3 and speed <= 3.0:
        notes.append("The files appear related, but alignment is not reliable enough for a mastering-dynamics verdict.")
        return "Inconclusive", notes
    notes.append("The files could not be aligned reliably enough to compare mastering dynamics.")
    return "Inconclusive", notes


def _similarity_label(score: float) -> str:
    if score < 60:
        return "Low"
    if score < 80:
        return "Moderate"
    if score < 90:
        return "High"
    if score < 97:
        return "Very High"
    return "Extremely High"


def _dynamics_similarity(status: str, short_term: dict[str, float]) -> dict[str, Any]:
    """Explainable 0..100 similarity index.

    Correlation is separately exposed as a direct Pearson measurement.  The
    combined score additionally penalizes large post-match residuals and a
    materially different robust short-term loudness span.  It is deliberately
    an explainable heuristic, not a probability.
    """
    if status == "Inconclusive":
        return {
            "score": None,
            "label": "Inconclusive",
            "loudness_curve_similarity_percent": None,
            "components": {},
        }

    r = _finite(short_term.get("correlation"))
    residual90 = _finite(short_term.get("residual_p90_abs_db"))
    span_delta = abs(_finite(short_term.get("span_delta_b_minus_a_db")))

    correlation_points = _piecewise(
        r,
        [(0.75, 0.0), (0.85, 30.0), (0.90, 55.0), (0.94, 75.0),
         (0.97, 90.0), (0.99, 97.0), (0.995, 99.0), (1.0, 100.0)],
    )
    residual_points = _piecewise(
        residual90,
        [(0.0, 100.0), (0.25, 100.0), (0.5, 96.0), (1.0, 86.0),
         (1.5, 72.0), (2.0, 55.0), (3.0, 25.0), (5.0, 0.0)],
    )
    span_points = _piecewise(
        span_delta,
        [(0.0, 100.0), (0.5, 97.0), (1.0, 91.0), (1.5, 82.0),
         (2.0, 72.0), (3.0, 52.0), (5.0, 20.0), (8.0, 0.0)],
    )

    score = round(0.55 * correlation_points + 0.30 * residual_points + 0.15 * span_points, 1)
    return {
        "score": score,
        "label": _similarity_label(score),
        "loudness_curve_similarity_percent": round(100.0 * r, 2) if np.isfinite(r) else None,
        "components": {
            "trajectory_correlation_points": round(correlation_points, 1),
            "residual_similarity_points": round(residual_points, 1),
            "loudness_span_similarity_points": round(span_points, 1),
            "weights": {
                "trajectory_correlation": 0.55,
                "residual_similarity": 0.30,
                "loudness_span_similarity": 0.15,
            },
        },
    }


def _musical_dynamics_advantage(status: str, short_term: dict[str, float], deltas: dict[str, float]) -> dict[str, Any]:
    """Direction of aligned Short-Term loudness dynamics, deliberately excluding DR/PLR.

    The robust aligned short-term span is primary. EBU LRA is corroborative.
    DR and PLR are peak/headroom-oriented and are compared later rather than
    being allowed to decide the loudness-dynamics direction circularly.
    """
    if status == "Inconclusive":
        return {
            "direction": "Inconclusive",
            "strength": "Inconclusive",
            "combined_delta_db": None,
            "reasoning": ["Reliable same-content alignment is required."],
        }

    span_delta = _finite(short_term.get("span_delta_b_minus_a_db"))
    lra_delta = _finite(deltas.get("lra_lu"))
    if not np.isfinite(span_delta):
        return {
            "direction": "Inconclusive",
            "strength": "Inconclusive",
            "combined_delta_db": None,
            "reasoning": ["Short-term loudness-span data are unavailable."],
        }

    # Opposing material changes in both direct loudness-range measures should
    # be exposed rather than averaged into a deceptively clean answer.
    if np.isfinite(lra_delta) and span_delta * lra_delta < 0 and abs(span_delta) >= 0.6 and abs(lra_delta) >= 0.6:
        return {
            "direction": "Mixed",
            "strength": "Mixed",
            "combined_delta_db": round(0.7 * span_delta + 0.3 * lra_delta, 2),
            "reasoning": [
                "Aligned short-term loudness span and EBU LRA point in opposite directions."
            ],
        }

    combined = span_delta if not np.isfinite(lra_delta) else 0.7 * span_delta + 0.3 * lra_delta
    magnitude = abs(combined)

    if magnitude < 0.60:
        direction = "None"
        strength = "None detected"
    elif magnitude < 1.50:
        direction = "B" if combined > 0 else "A"
        strength = "Slight"
    elif magnitude < 3.00:
        direction = "B" if combined > 0 else "A"
        strength = "Moderate"
    else:
        direction = "B" if combined > 0 else "A"
        strength = "Strong"

    reasoning: list[str] = []
    if direction == "None":
        reasoning.append("The robust aligned short-term loudness span is essentially unchanged.")
    else:
        filename = "Version B" if direction == "B" else "Version A"
        reasoning.append(f"{filename} shows the wider aligned Short-Term loudness span.")
    if np.isfinite(lra_delta):
        reasoning.append(f"EBU LRA changes by {lra_delta:+.2f} LU in Version B.")

    return {
        "direction": direction,
        "strength": strength,
        "combined_delta_db": round(combined, 2),
        "short_term_span_delta_b_minus_a_db": round(span_delta, 2),
        "lra_delta_b_minus_a_lu": round(lra_delta, 2) if np.isfinite(lra_delta) else None,
        "reasoning": reasoning,
    }


def _peak_structure(status: str, peak_crest: dict[str, float]) -> dict[str, Any]:
    if status == "Inconclusive":
        return {"score": None, "label": "Inconclusive", "direction": "Inconclusive"}

    peak_med = _finite(peak_crest.get("peak_lift_after_level_match_median_db"))
    crest_med = _finite(peak_crest.get("crest_delta_median_db"))
    peak_p90 = _finite(peak_crest.get("peak_lift_after_level_match_p90_db"))
    crest_p90 = _finite(peak_crest.get("crest_delta_p90_db"))

    med_vals = [abs(v) for v in (peak_med, crest_med) if np.isfinite(v)]
    p90_vals = [abs(v) for v in (peak_p90, crest_p90) if np.isfinite(v)]
    if not med_vals:
        return {"score": None, "label": "Unavailable", "direction": "Unavailable"}

    median_magnitude = float(np.median(med_vals))
    p90_magnitude = float(np.median(p90_vals)) if p90_vals else median_magnitude
    combined_magnitude = 0.60 * median_magnitude + 0.40 * p90_magnitude
    score = round(_piecewise(
        combined_magnitude,
        [(0.0, 0.0), (0.25, 10.0), (0.5, 25.0), (0.75, 40.0),
         (1.0, 55.0), (1.5, 75.0), (2.0, 90.0), (3.0, 100.0), (5.0, 100.0)],
    ), 1)

    if score < 20:
        label = "Low"
    elif score < 40:
        label = "Mild"
    elif score < 65:
        label = "Moderate"
    elif score < 85:
        label = "Strong"
    else:
        label = "Very Strong"

    # Direction is intentionally based on the robust median signs; the score
    # itself also considers p90 so intermittent regenerated peaks remain visible.
    significant = [("peak", peak_med), ("crest", crest_med)]
    sig = [v for _, v in significant if np.isfinite(v) and abs(v) >= 0.35]
    if len(sig) >= 2 and sig[0] * sig[1] < 0:
        direction = "Mixed"
    else:
        vals = [v for _, v in significant if np.isfinite(v)]
        center = float(np.median(vals)) if vals else 0.0
        direction = "B" if center > 0.20 else "A" if center < -0.20 else "None"

    return {
        "score": score,
        "label": label,
        "direction": direction,
        "combined_magnitude_db": round(combined_magnitude, 2),
        "median_magnitude_db": round(median_magnitude, 2),
        "p90_magnitude_db": round(p90_magnitude, 2),
        "meaning": "How strongly peak/crest structure differs after time alignment and loudness-level matching.",
    }


def _winner(delta_b_minus_a: float, threshold: float) -> str:
    if not np.isfinite(delta_b_minus_a):
        return "Unavailable"
    if delta_b_minus_a > threshold:
        return "B"
    if delta_b_minus_a < -threshold:
        return "A"
    return "Equal"


def _measured_dr(metrics_a: dict[str, Any], metrics_b: dict[str, Any]) -> dict[str, Any]:
    dr_a = _finite(metrics_a.get("dr"))
    dr_b = _finite(metrics_b.get("dr"))
    delta = dr_b - dr_a if np.isfinite(dr_a) and np.isfinite(dr_b) else float("nan")
    return {
        "version_a": round(dr_a, 1) if np.isfinite(dr_a) else None,
        "version_b": round(dr_b, 1) if np.isfinite(dr_b) else None,
        "delta_b_minus_a": round(delta, 1) if np.isfinite(delta) else None,
        "higher_measured_dr": _winner(delta, 0.45),
    }


def _peak_headroom(deltas: dict[str, float]) -> dict[str, Any]:
    plr_delta = _finite(deltas.get("plr_lu"))
    return {
        "plr_delta_b_minus_a_lu": round(plr_delta, 2) if np.isfinite(plr_delta) else None,
        "higher_plr": _winner(plr_delta, 0.75),
    }


def _comparison_conclusion(
    status: str,
    similarity: dict[str, Any],
    musical: dict[str, Any],
    measured_dr: dict[str, Any],
    peak_structure: dict[str, Any],
    peak_headroom: dict[str, Any],
    short_term: dict[str, float],
) -> dict[str, str]:
    if status == "Inconclusive":
        return {
            "code": "inconclusive",
            "title": "Inconclusive",
            "summary": "The files could not be aligned reliably enough for a mastering-dynamics verdict.",
        }

    dr_winner = measured_dr.get("higher_measured_dr", "Unavailable")
    musical_dir = musical.get("direction", "Inconclusive")
    peak_score = peak_structure.get("score")
    peak_score = float(peak_score) if peak_score is not None else 0.0
    plr_winner = peak_headroom.get("higher_plr", "Unavailable")
    level = _finite(short_term.get("level_offset_b_minus_a_db"), 0.0)
    sim_score = similarity.get("score")
    sim_score = float(sim_score) if sim_score is not None else 0.0

    # Pure gain changes cannot create a TT-DR advantage.  This branch therefore
    # requires measured DR *and* PLR to stay essentially equal while the musical
    # dynamics remain the same.
    if dr_winner == "Equal" and musical_dir == "None" and plr_winner == "Equal" and abs(level) >= 1.0 and peak_score < 40.0:
        return {
            "code": "primarily_level_shift",
            "title": "Primarily a level shift",
            "summary": "The versions differ in playback/master level, while measured DR, PLR and aligned Short-Term loudness dynamics remain essentially unchanged.",
        }

    if dr_winner in ("A", "B") and musical_dir == "None":
        if peak_score >= 40.0:
            return {
                "code": "dr_advantage_not_musical_peak_structure",
                "title": "Higher measured DR, but little loudness-dynamics advantage",
                "summary": f"Version {dr_winner} has the higher measured DR, but the aligned Short-Term loudness development is essentially unchanged. Altered peak/crest structure is a more plausible contributor to the DR difference than a comparable increase in aligned Short-Term loudness dynamics.",
            }
        return {
            "code": "dr_advantage_not_corroborated",
            "title": "Higher measured DR is not corroborated by loudness dynamics",
            "summary": f"Version {dr_winner} measures higher DR, but the aligned Short-Term loudness range does not show a corresponding advantage.",
        }

    if dr_winner in ("A", "B") and musical_dir == dr_winner:
        # If PLR points the opposite way, keep the result explicitly mixed even
        # though Short-Term loudness dynamics and TT DR agree.
        opposite = "A" if dr_winner == "B" else "B"
        if plr_winner == opposite:
            return {
                "code": "mixed_peak_vs_musical",
                "title": "Mixed evidence",
                "summary": f"Version {dr_winner} shows the wider Short-Term loudness range and higher measured DR, while peak-headroom evidence points the other way.",
            }
        strength = musical.get("strength", "")
        return {
            "code": "dr_advantage_corroborated",
            "title": "Higher measured DR is corroborated",
            "summary": f"Version {dr_winner} has the higher measured DR and also shows a {str(strength).lower()} advantage in aligned Short-Term loudness range.",
        }

    if dr_winner in ("A", "B") and musical_dir in ("A", "B") and musical_dir != dr_winner:
        return {
            "code": "dr_vs_musical_conflict",
            "title": "Measured DR and loudness dynamics disagree",
            "summary": f"Version {dr_winner} has the higher measured DR, but Version {musical_dir} shows the wider aligned Short-Term loudness range.",
        }

    if musical_dir == "Mixed":
        return {
            "code": "mixed_musical_metrics",
            "title": "Mixed loudness-dynamics evidence",
            "summary": "The aligned loudness-range measures do not agree strongly enough on a single dynamics advantage.",
        }

    if dr_winner == "Equal" and musical_dir in ("A", "B"):
        return {
            "code": "musical_difference_without_dr_difference",
            "title": "Loudness dynamics differ despite similar measured DR",
            "summary": f"Measured DR is essentially equal, while Version {musical_dir} shows the wider aligned Short-Term loudness range.",
        }

    if sim_score >= 97.0 and musical_dir == "None":
        return {
            "code": "essentially_same_dynamics",
            "title": "Essentially the same loudness dynamics",
            "summary": "The aligned Short-Term loudness development is extremely similar and no meaningful loudness-dynamics advantage is detected.",
        }

    return {
        "code": "uncertain",
        "title": "Uncertain",
        "summary": "The measured evidence does not support a simple one-direction dynamics conclusion.",
    }


def interpret_result(result: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen Dynamics Comparison v1.0 interpretation model."""
    status = str(result.get("alignment_status", "Inconclusive"))
    short_term = result.get("short_term_loudness") or {}
    peak_crest = result.get("peak_crest") or {}
    deltas = result.get("metric_deltas_b_minus_a") or {}
    metrics_a = (result.get("version_a") or {}).get("metrics") or {}
    metrics_b = (result.get("version_b") or {}).get("metrics") or {}

    similarity = _dynamics_similarity(status, short_term)
    musical = _musical_dynamics_advantage(status, short_term, deltas)
    peaks = _peak_structure(status, peak_crest)
    measured_dr = _measured_dr(metrics_a, metrics_b)
    headroom = _peak_headroom(deltas)
    conclusion = _comparison_conclusion(
        status, similarity, musical, measured_dr, peaks, headroom, short_term
    )

    return {
        "comparison_version": COMPARE_VERSION,
        "dynamics_similarity": similarity,
        "musical_dynamics_advantage": musical,
        "measured_dr": measured_dr,
        "peak_headroom": headroom,
        "peak_structure_difference": peaks,
        "level_difference_b_minus_a_db": round(_finite(short_term.get("level_offset_b_minus_a_db")), 2)
        if np.isfinite(_finite(short_term.get("level_offset_b_minus_a_db"))) else None,
        "conclusion": conclusion,
        "cautions": [
            "Loudness Dynamics Similarity is an explainable 0..100 score, not a statistical probability.",
            "Loudness Curve Similarity is the actual Pearson correlation after alignment and level matching.",
            "A pure gain change cannot increase TT DR; a higher DR with nearly identical aligned Short-Term loudness dynamics requires some additional waveform/peak difference.",
            "The comparison describes measurable relationships between these two files; it is not an audio-quality judgement.",
        ],
    }



def interpret_result_02(result: dict[str, Any]) -> dict[str, Any]:
    """Compatibility alias for stored Research 0.2 validation data."""
    return interpret_result(result)

def compare_files(
    path_a: Path,
    path_b: Path,
    metrics_a: dict[str, Any] | None = None,
    metrics_b: dict[str, Any] | None = None,
    progress_callback=None,
) -> dict[str, Any]:
    path_a = Path(path_a)
    path_b = Path(path_b)

    def progress(text: str) -> None:
        if progress_callback is not None:
            progress_callback(text)

    progress("Reading file information...")
    info_a = probe_basic(path_a)
    info_b = probe_basic(path_b)

    def existing_dr(metrics, path, label):
        if metrics:
            value = _finite(metrics.get("dr"))
            if np.isfinite(value) and value >= 0.0:
                return {
                    "dr": round(float(value), 1),
                    "dr_channels": metrics.get("dr_channels"),
                }
        progress(f"Measuring Version {label} DR...")
        return measure_masvis_dr(path)

    # Normal GUI use supplies the already-computed MasVis DR from each report,
    # so no redundant full-track DR pass is needed.  The bounded-memory fallback
    # remains available for standalone callers.
    dr_a = existing_dr(metrics_a, path_a, "A")
    dr_b = existing_dr(metrics_b, path_b, "B")

    progress("Extracting Version A loudness and peak trajectories...")
    series_a = extract_audio_series(path_a)
    progress("Extracting Version B loudness and peak trajectories...")
    series_b = extract_audio_series(path_b)

    fallback_a = {
        "integrated_lufs": series_a.integrated_lufs,
        "lra_lu": series_a.lra_lu,
        "true_peak_dbtp": series_a.true_peak_dbtp,
        "plr_lu": series_a.true_peak_dbtp - series_a.integrated_lufs,
        "dr": dr_a["dr"],
        "dr_channels": dr_a["dr_channels"],
    }
    fallback_b = {
        "integrated_lufs": series_b.integrated_lufs,
        "lra_lu": series_b.lra_lu,
        "true_peak_dbtp": series_b.true_peak_dbtp,
        "plr_lu": series_b.true_peak_dbtp - series_b.integrated_lufs,
        "dr": dr_b["dr"],
        "dr_channels": dr_b["dr_channels"],
    }
    effective_a = dict(fallback_a)
    effective_b = dict(fallback_b)
    if metrics_a:
        effective_a.update(metrics_a)
        effective_a.setdefault("dr", dr_a["dr"])
        effective_a.setdefault("dr_channels", dr_a["dr_channels"])
    if metrics_b:
        effective_b.update(metrics_b)
        effective_b.setdefault("dr", dr_b["dr"])
        effective_b.setdefault("dr_channels", dr_b["dr_channels"])

    progress("Aligning the two versions...")
    initial_offset, initial_r = estimate_global_lag(series_a.momentary_lufs, series_b.momentary_lufs)
    alignment = refine_linear_alignment(
        series_a.times, series_a.momentary_lufs,
        series_b.times, series_b.momentary_lufs,
        initial_offset,
    )
    alignment["initial_offset_seconds"] = initial_offset
    alignment["initial_global_correlation"] = initial_r

    offset = float(alignment["offset_seconds"])
    slope = float(alignment["slope"])

    _, ma, mb = aligned_values(
        series_a.times, series_a.momentary_lufs,
        series_b.times, series_b.momentary_lufs,
        offset, slope,
    )
    momentary = robust_series_stats(ma, mb)

    _, sa, sb = aligned_values(
        series_a.times, series_a.short_term_lufs,
        series_b.times, series_b.short_term_lufs,
        offset, slope,
    )
    short_term = robust_series_stats(sa, sb)

    _, pa, pb = aligned_values(
        series_a.times, series_a.peak_dbfs,
        series_b.times, series_b.peak_dbfs,
        offset, slope,
    )
    _, ca, cb = aligned_values(
        series_a.times, series_a.crest_db,
        series_b.times, series_b.crest_db,
        offset, slope,
    )
    count = min(pa.size, pb.size, ca.size, cb.size)
    if count >= 20:
        pa, pb, ca, cb = pa[:count], pb[:count], ca[:count], cb[:count]
        level_offset = _finite(momentary.get("level_offset_b_minus_a_db"), 0.0)
        peak_lift = (pb - level_offset) - pa
        crest_delta_arr = cb - ca
        peak_crest = {
            "count": int(count),
            "peak_lift_after_level_match_median_db": float(np.nanmedian(peak_lift)),
            "peak_lift_after_level_match_p90_db": float(np.nanpercentile(peak_lift, 90)),
            "crest_delta_median_db": float(np.nanmedian(crest_delta_arr)),
            "crest_delta_p90_db": float(np.nanpercentile(crest_delta_arr, 90)),
            "crest_correlation": float(np.corrcoef(ca, cb)[0, 1]) if np.std(ca) > 1e-6 and np.std(cb) > 1e-6 else float("nan"),
        }
    else:
        peak_crest = {"count": int(count)}

    deltas = {
        "integrated_lufs": _delta(effective_a, effective_b, "integrated_lufs"),
        "lra_lu": _delta(effective_a, effective_b, "lra_lu"),
        "plr_lu": _delta(effective_a, effective_b, "plr_lu"),
        "dr": _delta(effective_a, effective_b, "dr"),
        "crest_total_db": _delta(effective_a, effective_b, "crest_total_db"),
        "true_peak_dbtp": _delta(effective_a, effective_b, "true_peak_dbtp"),
        "allpass_recovery_median_db": _delta(effective_a, effective_b, "allpass_recovery_median_db"),
    }

    status, alignment_notes = _alignment_quality(momentary, alignment)
    result = {
        "comparison_version": COMPARE_VERSION,
        "version_a": {
            "path": str(path_a), "filename": path_a.name, "probe": info_a,
            "metrics": effective_a,
            "metrics_source": "Existing MasVis/Assessment result + compact FFmpeg trajectories" if metrics_a else "FFmpeg EBU R128 + streamed MasVis DR",
        },
        "version_b": {
            "path": str(path_b), "filename": path_b.name, "probe": info_b,
            "metrics": effective_b,
            "metrics_source": "Existing MasVis/Assessment result + compact FFmpeg trajectories" if metrics_b else "FFmpeg EBU R128 + streamed MasVis DR",
        },
        "alignment": alignment,
        "alignment_status": status,
        "alignment_notes": alignment_notes,
        "momentary_loudness": momentary,
        "short_term_loudness": short_term,
        "peak_crest": peak_crest,
        "metric_deltas_b_minus_a": deltas,
        "method_notes": [
            "Time alignment is derived from FFmpeg EBU R128 momentary loudness at 100 ms resolution.",
            "A linear drift term is allowed so small playback-speed differences can be represented.",
            "Level matching uses the median aligned momentary-loudness offset; peak matching is not used.",
            "Exact TT/MasVis DR is measured with a bounded-memory streaming implementation of the existing MasVis dynamic_range algorithm.",
            "Short-Term Loudness Curve Similarity is an actual Pearson correlation after alignment; it is not a probability.",
            "Loudness Dynamics Similarity is a separate explainable 0..100 v1 score; it is not a statistical probability.",
        ],
    }
    progress("Interpreting dynamics...")
    result["dynamics_comparison"] = interpret_result(result)
    progress("Dynamics comparison complete")
    return result
