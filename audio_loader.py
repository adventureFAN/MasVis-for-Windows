# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
"""Windows FFmpeg/ffprobe bridge used by MasVis for Windows.

This module mirrors the fixed-point input behavior used by the validated
Windows port.  It is intentionally separate from the MasVis analysis core.
"""

from __future__ import annotations

import builtins
import gettext
import json
import subprocess
from pathlib import Path

import numpy as np

from runtime_ffmpeg import (
    ffmpeg_executable,
    ffprobe_executable,
    subprocess_window_kwargs,
)

# MasVisGtk normally installs gettext ``_`` during GTK application startup.
# The Windows-native application imports the analysis core directly.
builtins._ = gettext.gettext


def probe_audio(path: Path):
    result = subprocess.run(
        [
            ffprobe_executable(),
            "-v", "error",
            "-of", "json",
            "-show_format",
            "-show_streams",
            "-select_streams", "a:0",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        **subprocess_window_kwargs(),
    )

    probe = json.loads(result.stdout)

    if not probe.get("streams"):
        raise RuntimeError("No audio stream found.")

    return probe


def load_audio(path: Path):
    probe = probe_audio(path)

    stream = probe["streams"][0]
    container = probe["format"]

    sample_rate = int(stream["sample_rate"])
    channels = int(stream["channels"])
    channel_layout = stream.get(
        "channel_layout",
        "stereo" if channels == 2 else "mono" if channels == 1 else "unknown",
    )

    bits = int(stream.get("bits_per_raw_sample") or 0)
    if bits <= 0:
        bits = int(stream.get("bits_per_sample") or 0)
    if bits <= 0:
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
        ffmpeg_executable(),
        "-v", "error",
        "-i", str(path),
        "-vn",
        "-f", ffmpeg_format,
        "-acodec", ffmpeg_codec,
        "-flags", "bitexact",
        "-",
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        **subprocess_window_kwargs(),
    )

    raw_data = np.frombuffer(result.stdout, dtype=dtype)

    if raw_data.size % channels != 0:
        raise RuntimeError("Decoded sample count does not match channel count.")

    raw_data = raw_data.reshape((channels, -1), order="F").copy(order="C")

    # FFmpeg emits 24-bit PCM in an s32le container.  MasVis expects the
    # effective 24-bit integer range, so restore it before float conversion.
    if bits == 24:
        raw_data //= 2**8

    float_data = raw_data.astype(float)
    float_data /= 2 ** (effective_bits - 1)

    samples = raw_data.shape[1]
    duration = samples / sample_rate

    tags = {
        k.lower(): v
        for k, v in container.get("tags", {}).items()
    }

    bitrate = (
        stream.get("bit_rate")
        or container.get("bit_rate")
        or "0"
    )

    track = {
        "data": {
            "fixed": raw_data,
            "float": float_data,
        },
        "samples": samples,
        "samplerate": sample_rate,
        "channels": channels,
        "channel_layout": channel_layout,
        "bitdepth": bits,
        "duration": duration,
        "format": container.get("format_name", ""),
        "metadata": {
            "size": int(container.get("size", 0)),
            "filename": path.name,
            "extension": path.suffix.lower().lstrip("."),
            "encoding": stream.get("codec_name", ""),
            "name": path.stem,
            "artist": tags.get("artist", ""),
            "title": tags.get("title", ""),
            "album": tags.get("album", ""),
            "track": tags.get("track", ""),
            "date": tags.get("date", ""),
            "bps": bitrate,
        },
        "raw_meta": "",
    }

    return track


def scalar(value):
    array = np.asarray(value)
    return float(array.flat[0])
