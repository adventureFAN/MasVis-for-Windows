# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Shared bounded-memory helpers for Dynamics Comparison.

FFmpeg extracts compact EBU R128 and peak/RMS time series at 100 ms resolution
so two long files do not need to remain fully decoded in Python memory.  The
module also contains a bounded-memory implementation of the existing MasVis
TT-style DR calculation for standalone comparison callers.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import correlate, correlation_lags

from runtime_ffmpeg import (
    ffmpeg_executable,
    ffprobe_executable,
    subprocess_window_kwargs,
)


SERIES_HOP_SECONDS = 0.1


@dataclass(frozen=True)
class AudioSeries:
    times: np.ndarray
    momentary_lufs: np.ndarray
    short_term_lufs: np.ndarray
    peak_dbfs: np.ndarray
    rms_dbfs: np.ndarray
    integrated_lufs: float = float("nan")
    lra_lu: float = float("nan")
    true_peak_dbtp: float = float("nan")

    @property
    def crest_db(self) -> np.ndarray:
        peak = np.asarray(self.peak_dbfs, dtype=float)
        rms = np.asarray(self.rms_dbfs, dtype=float)
        out = np.full_like(peak, np.nan)
        valid = np.isfinite(peak) & np.isfinite(rms)
        out[valid] = peak[valid] - rms[valid]
        return out


def _run_text(command: list[str]) -> str:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        **subprocess_window_kwargs(),
    )
    return result.stdout


def probe_basic(path: Path) -> dict[str, Any]:
    text = _run_text([
        ffprobe_executable(), "-v", "error", "-of", "json", "-show_format",
        "-show_streams", "-select_streams", "a:0", str(path),
    ])
    payload = json.loads(text)
    if not payload.get("streams"):
        raise RuntimeError(f"No audio stream found: {path}")
    stream = payload["streams"][0]
    fmt = payload.get("format", {})
    return {
        "duration_seconds": float(fmt.get("duration") or stream.get("duration") or 0.0),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "codec": stream.get("codec_name", ""),
        "format": fmt.get("format_name", ""),
        "size_bytes": int(fmt.get("size") or 0),
    }


def extract_ebu_series(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Return fixed-hop (time, momentary LUFS, short-term LUFS) via FFmpeg.

    ebur128 metadata frames are emitted every 100 ms.  Keeping the standardized
    K-weighted loudness trajectory outside Python's full-resolution audio path
    is both memory-light and close to the quantity we ultimately want to
    compare.
    """
    text = _run_text([
        ffmpeg_executable(), "-hide_banner", "-v", "error", "-i", str(path),
        "-af", "ebur128=metadata=1:peak=true,ametadata=print:file=-",
        "-f", "null", "-",
    ])

    times: list[float] = []
    momentary: list[float] = []
    short_term: list[float] = []
    current_time: float | None = None
    current_m: float | None = None
    current_s: float | None = None
    last_i = float("nan")
    last_lra = float("nan")
    last_true_peak_linear = float("nan")

    def flush() -> None:
        nonlocal current_time, current_m, current_s
        if current_time is not None and current_m is not None and current_s is not None:
            times.append(current_time)
            momentary.append(current_m)
            short_term.append(current_s)
        current_time = current_m = current_s = None

    for line in text.splitlines():
        if line.startswith("frame:"):
            flush()
            match = re.search(r"pts_time:([-+0-9.eE]+)", line)
            if match:
                current_time = float(match.group(1))
        elif line.startswith("lavfi.r128.M="):
            current_m = float(line.split("=", 1)[1])
        elif line.startswith("lavfi.r128.S="):
            current_s = float(line.split("=", 1)[1])
        elif line.startswith("lavfi.r128.I="):
            last_i = float(line.split("=", 1)[1])
        elif line.startswith("lavfi.r128.LRA="):
            last_lra = float(line.split("=", 1)[1])
        elif line.startswith("lavfi.r128.true_peak="):
            last_true_peak_linear = float(line.split("=", 1)[1])
    flush()

    if len(times) < 10:
        raise RuntimeError(f"Could not extract EBU R128 time series: {path}")
    true_peak_dbtp = (
        20.0 * math.log10(last_true_peak_linear)
        if np.isfinite(last_true_peak_linear) and last_true_peak_linear > 0.0
        else float("nan")
    )
    return (
        np.asarray(times, dtype=float),
        np.asarray(momentary, dtype=float),
        np.asarray(short_term, dtype=float),
        {
            "integrated_lufs": float(last_i),
            "lra_lu": float(last_lra),
            "true_peak_dbtp": float(true_peak_dbtp),
            "plr_lu": float(true_peak_dbtp - last_i) if np.isfinite(true_peak_dbtp) and np.isfinite(last_i) else float("nan"),
        },
    )


def extract_peak_rms_series(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return 100 ms Overall Peak/RMS series using FFmpeg astats.

    Audio is resampled to 48 kHz only inside FFmpeg, then framed into exactly
    4800-sample blocks.  Python receives only metadata text, not PCM buffers.
    """
    text = _run_text([
        ffmpeg_executable(), "-hide_banner", "-v", "error", "-i", str(path),
        "-af",
        "aresample=48000,asetnsamples=n=4800:p=0,"
        "astats=metadata=1:reset=1,ametadata=print:file=-",
        "-f", "null", "-",
    ])

    times: list[float] = []
    peak: list[float] = []
    rms: list[float] = []
    current_time: float | None = None
    current_peak: float | None = None
    current_rms: float | None = None

    def flush() -> None:
        nonlocal current_time, current_peak, current_rms
        if current_time is not None and current_peak is not None and current_rms is not None:
            times.append(current_time)
            peak.append(current_peak)
            rms.append(current_rms)
        current_time = current_peak = current_rms = None

    for line in text.splitlines():
        if line.startswith("frame:"):
            flush()
            match = re.search(r"pts_time:([-+0-9.eE]+)", line)
            if match:
                current_time = float(match.group(1))
        elif line.startswith("lavfi.astats.Overall.Peak_level="):
            current_peak = float(line.split("=", 1)[1])
        elif line.startswith("lavfi.astats.Overall.RMS_level="):
            current_rms = float(line.split("=", 1)[1])
    flush()

    if len(times) < 10:
        raise RuntimeError(f"Could not extract peak/RMS time series: {path}")
    return (
        np.asarray(times, dtype=float),
        np.asarray(peak, dtype=float),
        np.asarray(rms, dtype=float),
    )


def extract_audio_series(path: Path) -> AudioSeries:
    et, momentary, short_term, ebu = extract_ebu_series(path)
    at, peak, rms = extract_peak_rms_series(path)

    # Both FFmpeg chains are designed for 100 ms frames.  Small endpoint
    # differences are harmless; interpolate astats onto the EBU timeline.
    peak_i = np.interp(et, at, peak, left=np.nan, right=np.nan)
    rms_i = np.interp(et, at, rms, left=np.nan, right=np.nan)
    return AudioSeries(
        et, momentary, short_term, peak_i, rms_i,
        integrated_lufs=float(ebu["integrated_lufs"]),
        lra_lu=float(ebu["lra_lu"]),
        true_peak_dbtp=float(ebu["true_peak_dbtp"]),
    )


def measure_masvis_dr(path: Path) -> dict[str, Any]:
    """Measure the existing MasVis/TT DR value without retaining full PCM.

    This reproduces the Windows loader's decode semantics (including 24-bit
    S32LE reduction) and the upstream ``dynamic_range`` calculation block by
    block.  Only per-channel 3-second RMS/peak values are retained, so memory
    stays bounded even for long files.
    """
    path = Path(path)
    text = _run_text([
        ffprobe_executable(), "-v", "error", "-of", "json", "-show_format",
        "-show_streams", "-select_streams", "a:0", str(path),
    ])
    payload = json.loads(text)
    if not payload.get("streams"):
        raise RuntimeError(f"No audio stream found: {path}")
    stream = payload["streams"][0]
    sample_rate = int(stream.get("sample_rate") or 0)
    channels = int(stream.get("channels") or 0)
    if sample_rate <= 0 or channels <= 0:
        raise RuntimeError(f"Invalid audio stream parameters: {path}")

    bits = int(stream.get("bits_per_raw_sample") or 0)
    if bits <= 0:
        bits = int(stream.get("bits_per_sample") or 0)
    if bits <= 0:
        # Match the existing Windows smoke/app loader fallback for codecs such
        # as MP3/Opus that do not advertise an integer source bit depth.
        bits = 16

    if bits <= 8:
        ffmpeg_format = "s8"
        ffmpeg_codec = "pcm_s8"
        dtype = np.dtype("i1")
        effective_bits = 8
    elif bits <= 16:
        ffmpeg_format = "s16le"
        ffmpeg_codec = "pcm_s16le"
        dtype = np.dtype("<i2")
        effective_bits = 16
    else:
        ffmpeg_format = "s32le"
        ffmpeg_codec = "pcm_s32le"
        dtype = np.dtype("<i4")
        effective_bits = bits

    command = [
        ffmpeg_executable(), "-v", "error", "-i", str(path), "-vn",
        "-f", ffmpeg_format, "-acodec", ffmpeg_codec, "-flags", "bitexact", "-",
    ]
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **subprocess_window_kwargs(),
    )
    if proc.stdout is None or proc.stderr is None:
        raise RuntimeError("Could not start FFmpeg DR measurement")

    block_frames = 3 * sample_rate
    block_bytes = block_frames * channels * dtype.itemsize
    rms_blocks: list[np.ndarray] = []
    peak_blocks: list[np.ndarray] = []

    try:
        while True:
            chunk = proc.stdout.read(block_bytes)
            if not chunk:
                break
            raw = np.frombuffer(chunk, dtype=dtype)
            if raw.size == 0:
                continue
            if raw.size % channels != 0:
                raise RuntimeError(f"Decoded sample count does not match channel count: {path}")

            frames = raw.size // channels
            block = raw.reshape((channels, frames), order="F")
            if bits == 24:
                # Match smoke_test.py / the application loader exactly.
                block = block // (2 ** 8)

            data = block.astype(float)
            data /= 2 ** (effective_bits - 1)
            rms_blocks.append(np.sqrt(2.0 * ((data ** 2).mean(1))))
            peak_blocks.append(np.absolute(data).max(1))
    finally:
        proc.stdout.close()

    stderr = proc.stderr.read()
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace") or f"FFmpeg failed for {path}")
    if not rms_blocks or not peak_blocks:
        raise RuntimeError(f"No decoded audio samples for DR measurement: {path}")

    dr_rms = np.stack(rms_blocks, axis=1)
    dr_peak = np.stack(peak_blocks, axis=1)
    dr_rms.sort()
    dr_peak.sort()

    dr_20 = int(round(dr_rms.shape[1] * 0.2))
    if dr_20 < 1:
        dr_20 = 1
    if dr_peak.shape[1] < 2:
        return {"dr": -1.0, "dr_channels": None}

    with np.errstate(divide="ignore", invalid="ignore"):
        dr_ch = -20.0 * np.log10(
            np.sqrt((dr_rms[:, -dr_20:] ** 2).mean(1, keepdims=True))
            / dr_peak[:, [-2]]
        )
    if not np.all(np.isfinite(dr_ch)):
        return {"dr": -1.0, "dr_channels": None}

    dr = round(float(dr_ch.mean()), 1)
    if dr < 0:
        return {"dr": -1.0, "dr_channels": None}
    return {
        "dr": dr,
        "dr_channels": [round(float(v), 2) for v in dr_ch.ravel()],
    }


def _clean_for_alignment(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=float).copy()
    x[~np.isfinite(x)] = -70.0
    x = np.clip(x, -70.0, 5.0)
    # Ignore FFmpeg's initial ebur128 warm-up sentinel and keep silence finite.
    x[x < -69.0] = -70.0
    # Gentle 500 ms smoothing makes offset estimation less sensitive to
    # individual drum hits while retaining musical phrase timing.
    kernel = np.ones(5, dtype=float) / 5.0
    return np.convolve(x, kernel, mode="same")


def _zscore(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    std = float(np.std(x))
    if not np.isfinite(std) or std < 1e-9:
        return np.zeros_like(x)
    return (x - float(np.mean(x))) / std


def estimate_global_lag(a: np.ndarray, b: np.ndarray, hop_seconds: float = SERIES_HOP_SECONDS) -> tuple[float, float]:
    aa = _zscore(_clean_for_alignment(a))
    bb = _zscore(_clean_for_alignment(b))
    corr = correlate(bb, aa, mode="full", method="fft")
    lags = correlation_lags(bb.size, aa.size, mode="full")

    # Large unrelated offsets are possible, but for same-song mastering
    # comparisons a +/- 45 s guard avoids pathological matches on repeated
    # sections.  If the file is shorter, naturally use the available range.
    max_lag = int(round(45.0 / hop_seconds))
    allowed = np.abs(lags) <= max_lag
    if not np.any(allowed):
        raise RuntimeError("No valid alignment lag candidates")
    idx_local = int(np.argmax(corr[allowed]))
    idx = np.flatnonzero(allowed)[idx_local]
    lag_samples = int(lags[idx])

    # Definition used throughout: t_B ~= offset + slope * t_A.
    offset_seconds = -lag_samples * hop_seconds

    # Exact Pearson correlation on the overlap at this provisional lag.
    i0 = max(0, -lag_samples)
    i1 = min(aa.size, bb.size - lag_samples)
    if i1 - i0 < 20:
        return offset_seconds, 0.0
    a_seg = aa[i0:i1]
    b_seg = bb[i0 + lag_samples:i1 + lag_samples]
    r = float(np.corrcoef(a_seg, b_seg)[0, 1])
    return offset_seconds, r if np.isfinite(r) else 0.0


def _segment_corr(a: np.ndarray, b: np.ndarray) -> float:
    mask = np.isfinite(a) & np.isfinite(b)
    if int(mask.sum()) < 20:
        return float("nan")
    x = a[mask]
    y = b[mask]
    if float(np.std(x)) < 1e-6 or float(np.std(y)) < 1e-6:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def refine_linear_alignment(
    times_a: np.ndarray,
    loud_a: np.ndarray,
    times_b: np.ndarray,
    loud_b: np.ndarray,
    initial_offset: float,
) -> dict[str, Any]:
    """Fit t_B = offset + slope * t_A from local loudness anchors.

    This deliberately allows small speed differences (especially useful for
    vinyl captures) without time-stretching either source in the user-visible
    result.  A straight-line drift model is intentionally conservative for v0.1.
    """
    a = _clean_for_alignment(loud_a)
    b = _clean_for_alignment(loud_b)
    duration = min(float(times_a[-1]), float(times_b[-1]))
    if duration < 20.0:
        centers = np.linspace(5.0, max(5.0, duration - 5.0), 3)
        block_half = max(2.5, duration / 8.0)
    else:
        centers = np.linspace(max(8.0, duration * 0.08), duration * 0.92, 9)
        block_half = min(15.0, max(6.0, duration * 0.04))

    search_radius = 8.0
    offsets: list[float] = []
    anchor_times: list[float] = []
    anchor_corrs: list[float] = []

    for center in centers:
        mask_a = (times_a >= center - block_half) & (times_a <= center + block_half)
        if int(mask_a.sum()) < 30:
            continue
        ta = times_a[mask_a]
        xa = a[mask_a]

        candidate_offsets = np.arange(
            initial_offset - search_radius,
            initial_offset + search_radius + 0.0001,
            SERIES_HOP_SECONDS,
        )
        best_r = -2.0
        best_off = initial_offset
        for off in candidate_offsets:
            tb = off + ta
            valid = (tb >= times_b[0]) & (tb <= times_b[-1])
            if int(valid.sum()) < 20:
                continue
            yb = np.interp(tb[valid], times_b, b)
            r = _segment_corr(xa[valid], yb)
            if np.isfinite(r) and r > best_r:
                best_r = r
                best_off = float(off)
        if best_r > 0.25:
            anchor_times.append(float(center))
            offsets.append(best_off)
            anchor_corrs.append(float(best_r))

    if len(offsets) < 3:
        return {
            "offset_seconds": float(initial_offset),
            "slope": 1.0,
            "speed_difference_percent": 0.0,
            "anchor_count": len(offsets),
            "anchor_median_correlation": float(np.median(anchor_corrs)) if anchor_corrs else 0.0,
            "anchors": [
                {"time_a": t, "offset_b_minus_a": o, "correlation": r}
                for t, o, r in zip(anchor_times, offsets, anchor_corrs)
            ],
        }

    x = np.asarray(anchor_times, dtype=float)
    y = np.asarray(offsets, dtype=float)
    weights = np.clip(np.asarray(anchor_corrs, dtype=float), 0.05, 1.0)

    # Fit offset(t) = intercept + drift * t, then reject one round of large
    # residual outliers.  The time mapping slope is 1 + drift.
    coeff = np.polyfit(x, y, 1, w=weights)
    pred = np.polyval(coeff, x)
    resid = y - pred
    mad = float(np.median(np.abs(resid - np.median(resid))))
    keep = np.ones_like(x, dtype=bool)
    threshold = max(0.25, 3.5 * 1.4826 * mad)
    keep &= np.abs(resid) <= threshold
    if int(keep.sum()) >= 3 and int(keep.sum()) < len(x):
        coeff = np.polyfit(x[keep], y[keep], 1, w=weights[keep])

    drift, intercept = float(coeff[0]), float(coeff[1])
    slope = 1.0 + drift
    return {
        "offset_seconds": intercept,
        "slope": slope,
        "speed_difference_percent": (slope - 1.0) * 100.0,
        "anchor_count": int(keep.sum()),
        "anchor_median_correlation": float(np.median(np.asarray(anchor_corrs)[keep])) if np.any(keep) else 0.0,
        "anchors": [
            {"time_a": t, "offset_b_minus_a": o, "correlation": r, "used": bool(k)}
            for t, o, r, k in zip(anchor_times, offsets, anchor_corrs, keep)
        ],
    }


def aligned_values(
    times_a: np.ndarray,
    values_a: np.ndarray,
    times_b: np.ndarray,
    values_b: np.ndarray,
    offset_seconds: float,
    slope: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    tb = offset_seconds + slope * times_a
    valid = (
        np.isfinite(values_a)
        & (tb >= times_b[0])
        & (tb <= times_b[-1])
    )
    if not np.any(valid):
        return np.asarray([]), np.asarray([]), np.asarray([])
    va = np.asarray(values_a, dtype=float)[valid]
    vb = np.interp(tb[valid], times_b, np.asarray(values_b, dtype=float))
    ta = times_a[valid]
    finite = np.isfinite(va) & np.isfinite(vb)
    return ta[finite], va[finite], vb[finite]


def robust_series_stats(a: np.ndarray, b: np.ndarray, active_floor: float = -60.0) -> dict[str, float]:
    mask = np.isfinite(a) & np.isfinite(b) & (a > active_floor) & (b > active_floor)
    x = np.asarray(a, dtype=float)[mask]
    y = np.asarray(b, dtype=float)[mask]
    if x.size < 20:
        return {
            "count": float(x.size),
            "correlation": float("nan"),
            "level_offset_b_minus_a_db": float("nan"),
            "residual_median_abs_db": float("nan"),
            "residual_p90_abs_db": float("nan"),
            "span_a_db": float("nan"),
            "span_b_db": float("nan"),
            "span_delta_b_minus_a_db": float("nan"),
        }
    level_offset = float(np.median(y - x))
    y_match = y - level_offset
    r = _segment_corr(x, y_match)
    residual = y_match - x
    span_a = float(np.percentile(x, 90) - np.percentile(x, 10))
    span_b = float(np.percentile(y_match, 90) - np.percentile(y_match, 10))
    return {
        "count": float(x.size),
        "correlation": r,
        "level_offset_b_minus_a_db": level_offset,
        "residual_median_abs_db": float(np.median(np.abs(residual))),
        "residual_p90_abs_db": float(np.percentile(np.abs(residual), 90)),
        "span_a_db": span_a,
        "span_b_db": span_b,
        "span_delta_b_minus_a_db": span_b - span_a,
    }
