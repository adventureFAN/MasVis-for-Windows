# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 adventureFAN
import base64
import html
import io
import os
import sys
import threading
import traceback
from pathlib import Path

import matplotlib

# MasVis renders with Matplotlib; the Windows GUI itself is Qt.  Select the
# non-interactive backend before importing pyplot so worker-thread rendering
# never inherits an interactive Qt backend by accident.
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np

from PIL import Image

from PySide6.QtCore import (
    QByteArray,
    QObject,
    QPointF,
    QRectF,
    QSettings,
    QSize,
    QUrl,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFontDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStyle,
    QTabWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from audio_loader import AudioLoadCancelled, load_audio, scalar
from dynamics_assessment import assess_dynamics
from dynamics_compare import compare_files

from src.analysis import analyze
import src.output as masvis_output
from src.utils import Steps


PROJECT_DIR = Path(__file__).resolve().parent
APP_ICON = (
    PROJECT_DIR
    / "assets"
    / "app"
    / "masvis-for-windows.png"
)

WINDOWS_APP_ICON = (
    PROJECT_DIR
    / "assets"
    / "app"
    / "masvis-for-windows.ico"
)

DR_CHART_SVG = (
    PROJECT_DIR
    / "src"
    / "gtk"
    / "dynamic-range-chart.svg"
)

FLUENT_ICON_DIR = (
    PROJECT_DIR
    / "assets"
    / "icons"
    / "fluent"
)

FLUENT_ICON_FILES = {
    "open": "folder_open.svg",
    "advanced": "folder_multiple.svg",
    "save": "save.svg",
    "save_all": "save_multiple.svg",
    "compare": "item_compare.svg",
    "play": "play.svg",
    "compare_all": "image_multiple.svg",
    "assessment": "data_histogram.svg",
    "gif": "gif.svg",
    "settings": "settings.svg",
    "file_info": "document_text.svg",
    "help": "question_circle.svg",
    "about": "info.svg",
    "add_files": "document_add.svg",
    "add_folder": "folder_add.svg",
    "dismiss": "dismiss_20.svg",
}

CONTROL_ICON_FILES = {
    "chevron_dark": "chevron_down_dark.svg",
    "chevron_light": "chevron_down_light.svg",
    "chevron_up_dark": "chevron_up_dark.svg",
    "chevron_up_light": "chevron_up_light.svg",
}

APP_NAME = "MasVis for Windows"
APP_VERSION = "1.1.1"
SETTINGS_ORGANIZATION = "MasVis for Windows"
LEGACY_SETTINGS_ORGANIZATION = "MasVisGtk"
LEGACY_SETTINGS_APPLICATION = "MasVisGtk for Windows"
WINDOWS_APP_USER_MODEL_ID = "MasVis.ForWindows"

RENDER_SCALE = 3
ORIGINAL_VIEW_WIDTH = 1080
OVERVIEW_VIEW_WIDTH = 1212
OVERVIEW_ROW_HEIGHT = 192
TOOLBAR_ICON_SIZE = 24
HEADER_BUTTON_SIZE = 38
COMPARISON_PLOT_WIDTH = 606
COMPARISON_MIN_PLOT_WIDTH = 300
GIF_FRAME_WIDTH = 1080
GIF_FRAME_DURATION_MS = 3000

GIF_RESOLUTION_WIDTHS = {
    "Standard": 606,
    "High": 810,
    "Very High": 1080,
}
PROJECT_URL = "https://github.com/adventureFAN/MasVis-for-Windows"
UPSTREAM_PROJECT_URL = "https://github.com/itprojects/MasVisGtk"

REPORT_QUALITY_SCALES = {
    "Standard": 2,
    "High": 3,
    "Very High": 4,
}

EXPORT_RESOLUTION_WIDTHS = {
    "Standard": 606,
    "High": 1212,
    "Very High": 1818,
}

SAVE_FORMATS = {
    "PNG": {"extension": ".png", "filter": "PNG image (*.png)"},
    "JPEG": {"extension": ".jpg", "filter": "JPEG image (*.jpg *.jpeg)"},
    "SVG": {"extension": ".svg", "filter": "SVG image (*.svg)"},
    "WEBP": {"extension": ".webp", "filter": "WebP image (*.webp)"},
    "TIFF": {"extension": ".tiff", "filter": "TIFF image (*.tif *.tiff)"},
    "PDF": {"extension": ".pdf", "filter": "PDF document (*.pdf)"},
    "EPS": {"extension": ".eps", "filter": "EPS image (*.eps)"},
}

SUPPORTED_EXTENSIONS = {
    ".wav",
    ".flac",
    ".mp3",
    ".m4a",
    ".ogg",
    ".opus",
    ".aac",
    ".ac3",
    ".aiff",
    ".aif",
    ".amr",
    ".alac",
    ".pcm",
    ".wma",
    ".ape",
}

AUDIO_FILTER = (
    "Audio files "
    "(*.wav *.flac *.mp3 *.m4a *.ogg *.opus *.aac *.ac3 "
    "*.aiff *.aif *.amr *.alac *.pcm *.wma *.ape);;"
    "All files (*.*)"
)


# ============================================================
# Helpers
# ============================================================


def format_duration(seconds):
    seconds = max(0, int(round(float(seconds))))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def dr_color(dr):
    if dr is None or dr < 0:
        return "#303030"

    value = int(round(dr))

    if value <= 7:
        return "#ff0000"
    if value == 8:
        return "#ff4800"
    if value == 9:
        return "#ff9100"
    if value == 10:
        return "#ffd900"
    if value == 11:
        return "#d9ff00"
    if value == 12:
        return "#90ff00"
    if value == 13:
        return "#48ff00"

    return "#00ff00"


def assessment_color(label):
    """Value-neutral blue palette: intensity encodes evidence strength, not quality."""
    colors = {
        "Low": "#536878",
        "Mild": "#466b83",
        "Moderate": "#39708f",
        "High": "#2c759a",
        "Very High": "#1f7aa5",
    }
    return colors.get(str(label), "#555b64")


def comparison_similarity_color(label):
    """Value-neutral blue palette: intensity encodes similarity, not quality."""
    colors = {
        "Extremely High": "#1f7aa5",
        "Very High": "#2c759a",
        "High": "#39708f",
        "Moderate": "#466b83",
        "Low": "#536878",
        "Inconclusive": "#555b64",
    }
    return colors.get(str(label), "#555b64")


def qfont_from_string(value):
    if not value:
        return None

    font = QFont()

    if not font.fromString(str(value)):
        return None

    return font


def font_display_name(value):
    font = qfont_from_string(value)

    if font is None:
        return "Default"

    size = font.pointSizeF()

    if size > 0:
        return f"{font.family()} {size:g} pt"

    return font.family()


def matplotlib_font_settings(value):
    font = qfont_from_string(value)

    if font is None:
        return {}

    rc = {
        "font.family": [font.family()],
        "font.weight": int(font.weight()),
        "font.style": "italic" if font.italic() else "normal",
    }

    if font.pointSizeF() > 0:
        rc["font.size"] = float(font.pointSizeF())

    return rc


def image_format_from_path(path, selected_filter, default_format):
    suffix = Path(path).suffix.lower()

    for name, info in SAVE_FORMATS.items():
        if suffix == info["extension"]:
            return name

        if name == "JPEG" and suffix == ".jpeg":
            return name

        if name == "TIFF" and suffix == ".tif":
            return name

    for name, info in SAVE_FORMATS.items():
        if selected_filter == info["filter"]:
            return name

    return default_format


def save_report_image(
    png_data,
    output_path,
    save_format="PNG",
    export_resolution="High",
):
    """
    Save an already-rendered report in the selected output container.

    The Windows port currently keeps a raster report as the durable tab
    representation. PNG/JPEG/WebP/TIFF are direct raster exports. PDF/EPS
    are raster-backed document exports and SVG embeds the report raster in
    an SVG container. Export never upscales beyond the rendered source.
    """

    save_format = str(save_format).upper()

    if save_format not in SAVE_FORMATS:
        save_format = "PNG"

    export_resolution = (
        export_resolution
        if export_resolution in EXPORT_RESOLUTION_WIDTHS
        else "High"
    )

    info = SAVE_FORMATS[save_format]
    output_path = Path(output_path)

    if output_path.suffix.lower() not in {
        info["extension"],
        ".jpeg" if save_format == "JPEG" else info["extension"],
        ".tif" if save_format == "TIFF" else info["extension"],
    }:
        output_path = output_path.with_suffix(info["extension"])

    with Image.open(io.BytesIO(png_data)) as source:
        image = source.convert("RGB")

        target_width = min(
            int(EXPORT_RESOLUTION_WIDTHS[export_resolution]),
            int(image.width),
        )

        if target_width > 0 and target_width != image.width:
            scale = float(target_width) / float(image.width)
            target_height = max(1, int(round(image.height * scale)))
            image = image.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS,
            )

        if save_format == "SVG":
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{image.width}" height="{image.height}" '
                f'viewBox="0 0 {image.width} {image.height}">\n'
                f'  <image width="{image.width}" height="{image.height}" '
                f'href="data:image/png;base64,{encoded}"/>\n'
                f'</svg>\n'
            )
            output_path.write_text(svg, encoding="utf-8")

        elif save_format == "JPEG":
            quality = {
                "Standard": 90,
                "High": 95,
                "Very High": 98,
            }[export_resolution]
            image.save(
                output_path,
                format="JPEG",
                quality=quality,
                optimize=True,
                subsampling=0,
            )

        elif save_format == "WEBP":
            quality = {
                "Standard": 88,
                "High": 95,
                "Very High": 100,
            }[export_resolution]
            image.save(
                output_path,
                format="WEBP",
                quality=quality,
                method=6,
            )

        elif save_format == "TIFF":
            image.save(
                output_path,
                format="TIFF",
                compression="tiff_deflate",
            )

        elif save_format == "PDF":
            image.save(
                output_path,
                format="PDF",
                resolution=300.0,
            )

        elif save_format == "EPS":
            image.save(
                output_path,
                format="EPS",
            )

        else:
            image.save(
                output_path,
                format="PNG",
                optimize=True,
            )

    return output_path


def apply_report_theme_to_png(png_data, report_theme="Light"):
    """
    Apply the optional Windows report theme after the canonical MasVis render.

    The Light path returns the original PNG bytes unchanged, preserving exact
    upstream/Windows render parity. Dark mode remaps neutral report tones only
    (background, text, axes, grids and grey annotations) while deliberately
    preserving saturated plot colours such as the existing blue/red channels.
    """

    if str(report_theme).strip().lower() != "dark":
        return png_data

    with Image.open(io.BytesIO(png_data)) as source:
        rgba = source.convert("RGBA")
        array = np.asarray(rgba, dtype=np.uint8).copy()

    # Process the report in bounded row strips. High-resolution reports can be
    # large, and a full-image float working set would undermine the existing
    # RAM optimization work for no analytical benefit.
    strip_rows = 256

    for top in range(0, array.shape[0], strip_rows):
        bottom = min(array.shape[0], top + strip_rows)
        rgb = array[top:bottom, :, :3].astype(np.uint16)

        channel_max = rgb.max(axis=2)
        channel_min = rgb.min(axis=2)
        chroma = channel_max - channel_min

        # Integer approximation of Rec.709 luminance: weights sum to 256.
        luminance = (
            54 * rgb[:, :, 0]
            + 183 * rgb[:, :, 1]
            + 19 * rgb[:, :, 2]
        ) >> 8

        # Upstream report chrome is neutral (white/black/grey). Restrict the
        # palette inversion to near-neutral pixels so channel colours and
        # other signal-specific saturated artwork retain their meaning.
        neutral = chroma <= 28
        remapped = 235 - ((82 * luminance) // 100)
        remapped = np.clip(remapped, 24, 235).astype(np.uint8)

        target = array[top:bottom, :, :3]
        for channel in range(3):
            values = target[:, :, channel]
            values[neutral] = remapped[neutral]

    output = io.BytesIO()
    Image.fromarray(array, mode="RGBA").save(
        output,
        format="PNG",
        optimize=True,
    )
    return output.getvalue()


def render_high_resolution(
    track,
    analysis,
    header,
    r128_unit="LUFS",
    render_overview=False,
    callback=None,
    render_scale=RENDER_SCALE,
    report_font="",
):
    """
    Render the existing MasVis report at higher raster resolution while
    preserving the same relative plot geometry and analysis values.
    """

    original_dpi = masvis_output.DPI
    original_positions = masvis_output.positions
    original_footer_label = masvis_output.REPORT_FOOTER_LABEL

    render_scale = max(1, int(render_scale))

    def scaled_positions(nc=1):
        pos = dict(original_positions(nc))
        pos["w"] *= render_scale
        pos["h"] *= render_scale
        return pos

    try:
        masvis_output.DPI = original_dpi * render_scale
        masvis_output.positions = scaled_positions
        masvis_output.REPORT_FOOTER_LABEL = f"{APP_NAME} {APP_VERSION}"

        with matplotlib.rc_context(
            rc=matplotlib_font_settings(report_font)
        ):
            return masvis_output.render(
                track=track,
                analysis=analysis,
                header=header,
                r128_unit=r128_unit,
                render_overview=render_overview,
                callback=callback,
            )
    finally:
        masvis_output.DPI = original_dpi
        masvis_output.positions = original_positions
        masvis_output.REPORT_FOOTER_LABEL = original_footer_label


def render_modern_overview_row(
    track,
    analysis,
    header,
    r128_unit="LUFS",
    report_font="",
):
    """
    Render one Overview row using the geometry of modern MasVisGtk's
    interactive GTK renderer rather than the legacy 606x64 export overview.

    Modern MasVisGtk uses a 1212 px overview canvas and displays, at right:
    DR, Peak, Crest and L_k. This Windows raster version preserves that
    information and honors the selected LUFS/LU display unit.
    """

    previous_font_rc = {
        key: matplotlib.rcParams[key]
        for key in ("font.family", "font.weight", "font.style", "font.size")
    }
    custom_font_rc = matplotlib_font_settings(report_font)
    matplotlib.rcParams.update(custom_font_rc)

    width = OVERVIEW_VIEW_WIDTH
    height = OVERVIEW_ROW_HEIGHT
    waveform_height = 128
    dpi = 100

    data = track["data"]["float"]
    channels = int(track["channels"])
    sample_rate = int(track["samplerate"])
    metadata = track["metadata"]

    dr = float(analysis["dr"])
    peak = float(np.max(analysis["peak_dbfs"]))
    crest = float(analysis["crest_total_db"])
    loudness = float(analysis["l_kg"])

    unit = str(r128_unit).upper()
    if unit == "LU":
        loudness += 23.0
    else:
        unit = "LUFS"

    # Build the channel-composited waveform the same way the modern GTK
    # renderer does: each channel is rendered independently and the RGB
    # layers are multiplied, which makes overlapping L/R regions black.
    fig_buf = plt.figure(
        figsize=(width / dpi, waveform_height / dpi),
        dpi=dpi,
        facecolor="white",
    )
    ax_buf = fig_buf.add_axes([0, 0, 1, 1])
    ax_buf.axis("off")
    ax_buf.set_ylim(-1, 1)
    ax_buf.set_xticks([])
    ax_buf.set_yticks([])

    fig_buf.canvas.draw()
    w, h = fig_buf.canvas.get_width_height()

    img_buf = np.zeros((h, w, 4), np.uint8)
    img_buf[:, :, 0:3] = 255

    colors = getattr(masvis_output, "c_color", ["blue", "red"])

    try:
        for index, channel in enumerate(data):
            ax_buf.clear()
            ax_buf.axis("off")
            ax_buf.set_position([0, 0, 1, 1])
            ax_buf.set_ylim(-1, 1)
            ax_buf.set_xticks([])
            ax_buf.set_yticks([])

            new_ch, _new_n, _new_r = masvis_output.pixelize(
                channel,
                ax_buf,
                which="both",
                oversample=2,
            )

            color = colors[index % len(colors)]
            ax_buf.plot(
                range(len(new_ch)),
                new_ch,
                color=color,
                linewidth=1.0,
            )
            ax_buf.set_xlim(0, max(1, len(new_ch)))

            fig_buf.canvas.draw()
            img = np.frombuffer(
                fig_buf.canvas.buffer_rgba(),
                np.uint8,
            ).reshape(h, w, -1)

            img_buf[:, :, 0:3] = (
                img[:, :, 0:3]
                * (img_buf[:, :, 0:3] / 255.0)
            )
            img_buf[:, :, -1] = np.maximum(
                img[:, :, -1],
                img_buf[:, :, -1],
            )
    finally:
        plt.close(fig_buf)

    img_buf[:, :, 0:3] = (
        (img_buf[:, :, 3:4] / 255.0)
        * img_buf[:, :, 0:3]
        + (255 - img_buf[:, :, 3:4])
    )
    img_buf[:, :, -1] = 255

    # Compose the actual overview row. The proportions mirror modern
    # output_gtk.py: waveform occupies ~78% and the statistics sit right.
    fig = plt.figure(
        figsize=(width / dpi, height / dpi),
        dpi=dpi,
        facecolor="white",
    )

    ax = fig.add_axes([0.04, 0.14, 0.78, 0.67])
    ax.imshow(
        img_buf,
        aspect="auto",
        interpolation="none",
    )
    ax.set_xticks([])
    ax.set_yticks([])

    bitrate = int(metadata.get("bps") or 0)
    bitrate_text = (
        str(int(round(bitrate / 1000.0)))
        if bitrate
        else "~"
    )

    title_text = (
        f"{header} "
        f"[{metadata.get('encoding', '')}, "
        f"{channels} channels, "
        f"{track['bitdepth']} bits, "
        f"{sample_rate / 1000.0:.1f} kHz, "
        f"{bitrate_text} kbps]"
    )

    fig.text(
        0.04,
        0.91,
        title_text,
        fontsize=10,
        color="black",
        ha="left",
        va="top",
    )

    info_text = (
        f"DR = {dr:.1f}\n"
        f"Peak = {peak:.1f} dBFS\n"
        f"Crest = {crest:.1f} dB\n"
        f"L$_k$ = {loudness:.1f} {unit}"
    )

    fig.text(
        0.835,
        0.76,
        info_text,
        fontsize=10,
        color="black",
        ha="left",
        va="top",
        linespacing=1.15,
    )

    output = io.BytesIO()
    fig.savefig(
        output,
        format="png",
        dpi=dpi,
        facecolor="white",
        edgecolor="none",
    )
    plt.close(fig)

    png_data = output.getvalue()

    for key, value in previous_font_rc.items():
        matplotlib.rcParams[key] = value

    return png_data


def compose_overview_png(row_pngs):
    """Combine MasVis overview rows into one vertically stacked PNG."""

    images = []

    for row_png in row_pngs:
        image = Image.open(io.BytesIO(row_png)).convert("RGB")
        images.append(image.copy())
        image.close()

    if not images:
        return None

    width = max(image.width for image in images)
    height = sum(image.height for image in images)

    combined = Image.new("RGB", (width, height), "white")

    y = 0
    for image in images:
        combined.paste(image, (0, y))
        y += image.height

    output = io.BytesIO()
    combined.save(output, format="PNG")
    return output.getvalue()


# ============================================================
# Theme
# ============================================================


THEME_DARK = {
    "window": "#202020",
    "header": "#2b2b2b",
    "header_border": "#151515",
    "text": "#ededed",
    "muted": "#a5a5a5",
    "button_hover": "#3a3a3a",
    "button_pressed": "#484848",
    "button_border": "#4a4a4a",
    "tab": "#292929",
    "tab_hover": "#343434",
    "tab_selected": "#3b3b3b",
    "tab_border": "#414141",
    "menu": "#303030",
    "menu_border": "#4a4a4a",
    "scroll": "#232323",
    "scroll_handle": "#555555",
    "zoom": "#050505",
    "dialog": "#2c2c2c",
    "progress_bg": "#1d1d1d",
    "progress_chunk": "#5c85c3",
}

THEME_LIGHT = {
    "window": "#f3f3f3",
    "header": "#eeeeee",
    "header_border": "#d2d2d2",
    "text": "#1f1f1f",
    "muted": "#6b6b6b",
    "button_hover": "#e1e1e1",
    "button_pressed": "#d5d5d5",
    "button_border": "#c9c9c9",
    "tab": "#e9e9e9",
    "tab_hover": "#dddddd",
    "tab_selected": "#ffffff",
    "tab_border": "#cfcfcf",
    "menu": "#ffffff",
    "menu_border": "#c8c8c8",
    "scroll": "#ededed",
    "scroll_handle": "#b5b5b5",
    "zoom": "#111111",
    "dialog": "#f4f4f4",
    "progress_bg": "#e5e5e5",
    "progress_chunk": "#4f7fc7",
}


def detect_system_dark(app):
    """
    Prefer Qt's Windows system color-scheme API. Fall back to palette
    luminance if the installed Qt binding does not expose it.
    """
    try:
        scheme = app.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except Exception:
        color = app.palette().window().color()
        luminance = (
            0.2126 * color.red()
            + 0.7152 * color.green()
            + 0.0722 * color.blue()
        )
        return luminance < 128


def build_stylesheet(dark):
    t = THEME_DARK if dark else THEME_LIGHT
    combo_arrow = (
        FLUENT_ICON_DIR
        / (
            CONTROL_ICON_FILES["chevron_light"]
            if dark
            else CONTROL_ICON_FILES["chevron_dark"]
        )
    ).as_posix()
    spin_up_arrow = (
        FLUENT_ICON_DIR
        / (
            CONTROL_ICON_FILES["chevron_up_light"]
            if dark
            else CONTROL_ICON_FILES["chevron_up_dark"]
        )
    ).as_posix()
    spin_down_arrow = (
        FLUENT_ICON_DIR
        / (
            CONTROL_ICON_FILES["chevron_light"]
            if dark
            else CONTROL_ICON_FILES["chevron_dark"]
        )
    ).as_posix()
    tab_close_icon = (
        FLUENT_ICON_DIR
        / (
            "dismiss_tab_light.svg"
            if dark
            else "dismiss_tab_dark.svg"
        )
    ).as_posix()

    return f"""
    QWidget#root {{
        background-color: {t["window"]};
        color: {t["text"]};
    }}

    QWidget#contentArea {{
        background-color: {t["window"]};
    }}

    QFrame#header {{
        background-color: {t["header"]};
        border: none;
        border-bottom: 1px solid {t["header_border"]};
    }}

    QFrame#advancedToolbar {{
        background-color: {t["header"]};
        border: none;
        border-bottom: 1px solid {t["header_border"]};
    }}

    QFrame#advancedOptions {{
        background-color: {t["tab"]};
        border: 1px solid {t["tab_border"]};
        border-radius: 7px;
    }}

    QLabel#advancedSectionTitle {{
        color: {t["text"]};
        font-weight: 600;
    }}

    QLabel#advancedCount {{
        color: {t["muted"]};
    }}

    QListWidget#advancedList {{
        background-color: {t["window"]};
        color: {t["text"]};
        border: 1px solid {t["tab_border"]};
        border-radius: 7px;
        outline: none;
        padding: 3px;
    }}

    QListWidget#advancedList::item {{
        border: none;
        padding: 0px;
    }}

    QWidget#advancedPathRow {{
        background-color: transparent;
    }}

    QLabel#advancedPathLabel {{
        color: {t["text"]};
    }}

    QToolButton#removePathButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 3px;
    }}

    QToolButton#removePathButton:hover {{
        background-color: {t["button_hover"]};
        border-color: {t["button_border"]};
    }}

    QComboBox {{
        background-color: {t["header"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 5px;
        padding: 5px 26px 5px 8px;
        min-height: 20px;
    }}

    QComboBox:hover {{
        border-color: {t["muted"]};
    }}

    QComboBox QAbstractItemView {{
        background-color: {t["menu"]};
        color: {t["text"]};
        selection-background-color: {t["button_hover"]};
        border: 1px solid {t["menu_border"]};
    }}

    QLineEdit {{
        background-color: {t["header"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 5px;
        padding: 4px 7px;
        min-height: 22px;
        selection-background-color: #6e9ad6;
        selection-color: white;
    }}

    QLineEdit:focus {{
        border-color: #6e9ad6;
    }}

    QAbstractItemView {{
        background-color: {t["menu"]};
        color: {t["text"]};
        border: 1px solid {t["menu_border"]};
        outline: none;
        selection-background-color: {t["button_pressed"]};
        selection-color: {t["text"]};
    }}

    QGroupBox {{
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 6px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 8px;
        padding: 0px 4px;
    }}

    QGroupBox:disabled {{
        color: {t["muted"]};
    }}

    QCheckBox {{
        color: {t["text"]};
        spacing: 7px;
    }}

    QFrame#compareRow {{
        background-color: transparent;
        border: none;
        border-bottom: 1px solid {t["tab_border"]};
    }}

    QLabel#comparePath {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QLabel#compareHint {{
        color: {t["muted"]};
        font-size: 12px;
    }}

    QScrollArea#compareScroll {{
        background-color: {t["window"]};
        border: 1px solid {t["button_border"]};
        border-radius: 7px;
    }}

    QWidget#compareListBody {{
        background-color: {t["window"]};
    }}

    QWidget#comparisonContent {{
        background-color: {t["window"]};
    }}

    QLabel#preferencesSectionTitle {{
        color: {t["text"]};
        font-size: 13px;
        font-weight: 700;
        padding-top: 2px;
    }}

    QFrame#preferencesGroup {{
        background-color: {t["header"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
    }}

    QLabel#preferencesValue {{
        color: {t["muted"]};
    }}

    QLabel#fileInfoTitle {{
        color: {t["text"]};
        font-size: 16px;
        font-weight: 700;
    }}

    QLabel#fileInfoSubtitle {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QLabel#fileInfoSectionTitle {{
        color: {t["text"]};
        font-size: 13px;
        font-weight: 700;
        padding-top: 2px;
    }}

    QFrame#fileInfoGroup {{
        background-color: {t["header"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
    }}

    QLabel#fileInfoKey {{
        color: {t["muted"]};
    }}

    QLabel#fileInfoValue {{
        color: {t["text"]};
    }}

    QLabel#fileInfoCopied {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QLabel#assessmentTitle {{
        color: {t["text"]};
        font-size: 16px;
        font-weight: 700;
    }}

    QLabel#assessmentSubtitle {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QFrame#assessmentScoreCard {{
        background-color: {t["header"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
    }}

    QLabel#assessmentIndexName {{
        color: {t["muted"]};
        font-size: 11px;
        font-weight: 700;
    }}

    QLabel#assessmentScoreValue {{
        font-family: Consolas, "Courier New", monospace;
        font-size: 24px;
        font-weight: 700;
    }}

    QLabel#assessmentSummary {{
        color: {t["text"]};
        font-size: 12px;
    }}

    QLabel#assessmentConfidence {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QTextBrowser#assessmentDetails {{
        background-color: {t["header"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
        padding: 10px;
        selection-background-color: #6e9ad6;
    }}

    QLabel#assessmentCopied {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QListWidget#helpNavigation {{
        background-color: {t["header"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
        outline: none;
        padding: 4px;
    }}

    QListWidget#helpNavigation::item {{
        padding: 6px 10px;
        border-radius: 5px;
    }}

    QListWidget#helpNavigation::item:hover {{
        background-color: {t["button_hover"]};
    }}

    QListWidget#helpNavigation::item:selected {{
        background-color: {t["button_pressed"]};
        color: {t["text"]};
    }}

    QTextBrowser#helpText {{
        background-color: {t["header"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
        padding: 10px;
        selection-background-color: #6e9ad6;
    }}

    QLabel#shortcutsSectionTitle {{
        color: {t["text"]};
        font-size: 13px;
        font-weight: 700;
        padding-top: 2px;
    }}

    QFrame#shortcutsGroup {{
        background-color: {t["header"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
    }}

    QLabel#shortcutAction {{
        color: {t["text"]};
    }}

    QLabel#shortcutKey {{
        background-color: {t["button_hover"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 5px;
        padding: 3px 8px;
        font-family: Consolas, "Courier New", monospace;
        font-weight: 600;
    }}

    QLabel#aboutTitle {{
        color: {t["text"]};
        font-size: 21px;
        font-weight: 700;
    }}

    QLabel#aboutVersion {{
        color: {t["muted"]};
        font-size: 12px;
    }}

    QLabel#aboutDescription {{
        color: {t["text"]};
        font-size: 12px;
    }}

    QFrame#aboutGroup {{
        background-color: {t["header"]};
        border: 1px solid {t["button_border"]};
        border-radius: 8px;
    }}

    QLabel#aboutSectionTitle {{
        color: {t["text"]};
        font-size: 12px;
        font-weight: 700;
    }}

    QLabel#aboutMuted {{
        color: {t["muted"]};
        font-size: 11px;
    }}

    QComboBox, QSpinBox {{
        background-color: {t["button_hover"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 5px;
        padding: 4px 7px;
        min-height: 22px;
    }}

    QComboBox {{
        padding-right: 28px;
    }}

    QSpinBox {{
        padding-right: 24px;
    }}

    QComboBox:hover, QSpinBox:hover {{
        border-color: {t["muted"]};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {t["button_border"]};
        background: transparent;
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
    }}

    QComboBox::down-arrow {{
        image: url({combo_arrow});
        width: 12px;
        height: 12px;
    }}

    QSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 18px;
        border-left: 1px solid {t["button_border"]};
        border-bottom: 1px solid {t["button_border"]};
        background: transparent;
        border-top-right-radius: 5px;
    }}

    QSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 18px;
        border-left: 1px solid {t["button_border"]};
        background: transparent;
        border-bottom-right-radius: 5px;
    }}

    QSpinBox::up-button:hover, QComboBox::drop-down:hover, QSpinBox::down-button:hover {{
        background-color: {t["button_pressed"]};
    }}

    QSpinBox::up-arrow {{
        image: url({spin_up_arrow});
        width: 10px;
        height: 10px;
    }}

    QSpinBox::down-arrow {{
        image: url({spin_down_arrow});
        width: 10px;
        height: 10px;
    }}

    QToolButton#headerIconButton {{
        background-color: transparent;
        color: {t["text"]};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
    }}

    QToolButton#headerIconButton:hover {{
        background-color: {t["button_hover"]};
        border-color: {t["button_border"]};
    }}

    QToolButton#headerIconButton:pressed {{
        background-color: {t["button_pressed"]};
    }}

    QToolButton#headerIconButton:disabled {{
        background-color: transparent;
        border-color: transparent;
        opacity: 0.45;
    }}

    QToolButton#headerIconButton::menu-indicator {{
        image: none;
        width: 0px;
    }}

    QLabel#emptyPage {{
        color: {t["muted"]};
        background-color: {t["window"]};
        font-size: 14px;
    }}

    QTabWidget#reportTabs::pane {{
        border: none;
        background-color: {t["window"]};
    }}

    QTabBar {{
        background-color: {t["header"]};
    }}

    QTabBar::tab {{
        background-color: {t["tab"]};
        color: {t["text"]};
        border: none;
        border-right: 1px solid {t["tab_border"]};
        border-bottom: 1px solid {t["header_border"]};
        padding: 3px 9px;
    }}

    QTabBar::tab:hover {{
        background-color: {t["tab_hover"]};
    }}

    QTabBar::tab:selected {{
        background-color: {t["tab_selected"]};
        color: {t["text"]};
        border-bottom: 2px solid #6e9ad6;
    }}

    QTabBar::close-button {{
        image: url({tab_close_icon});
        width: 14px;
        height: 14px;
        margin-left: 4px;
        margin-right: 4px;
        border-radius: 3px;
    }}

    QTabBar::close-button:hover {{
        background-color: {t["button_pressed"]};
    }}

    QScrollArea#reportScroll {{
        background-color: {t["window"]};
        border: none;
    }}

    QLabel#reportImage {{
        background-color: white;
        border: none;
    }}

    QMenu {{
        background-color: {t["menu"]};
        color: {t["text"]};
        border: 1px solid {t["menu_border"]};
        border-radius: 6px;
        padding: 5px;
    }}

    QMenu::item {{
        padding: 7px 34px 7px 12px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {t["button_hover"]};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {t["menu_border"]};
        margin: 5px 6px;
    }}

    QFrame#zoomFrame {{
        background-color: {t["zoom"]};
        border: 2px solid #f2f2f2;
        border-radius: 19px;
    }}

    QFrame#zoomFrame QPushButton {{
        background-color: transparent;
        color: white;
        border: none;
        border-radius: 0px;
        padding: 2px 9px;
        font-weight: 700;
    }}

    QFrame#zoomFrame QPushButton:hover {{
        background-color: #414141;
    }}

    QFrame#zoomFrame QPushButton:pressed {{
        background-color: #555555;
    }}

    QFrame#zoomFrame QPushButton:disabled {{
        color: white;
        background-color: transparent;
    }}

    QPushButton#zoomOutButton {{
        border-top-left-radius: 15px;
        border-bottom-left-radius: 15px;
    }}

    QPushButton#zoomInButton {{
        border-top-right-radius: 15px;
        border-bottom-right-radius: 15px;
    }}

    QPushButton#zoomIndicator {{
        font-family: Consolas, "Courier New", monospace;
        font-weight: 700;
    }}

    QDialog {{
        background-color: {t["dialog"]};
        color: {t["text"]};
    }}

    QDialog QLabel {{
        color: {t["text"]};
    }}

    QLabel#processingCounter {{
        font-family: Consolas, "Courier New", monospace;
        font-size: 17px;
        font-weight: 700;
    }}

    QLabel#processingFilename {{
        font-size: 13px;
        color: {t["text"]};
    }}

    QLabel#processingStatus {{
        font-size: 12px;
        color: {t["muted"]};
    }}

    QLabel#channelLayoutTitle {{
        font-size: 15px;
        font-weight: 700;
    }}

    QLabel#channelDRValue {{
        font-family: Consolas, "Courier New", monospace;
        font-weight: 700;
    }}

    QPushButton {{
        background-color: {t["button_hover"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 6px;
        padding: 6px 10px;
    }}

    QPushButton:hover {{
        background-color: {t["button_pressed"]};
    }}

    QPushButton:disabled {{
        color: {t["muted"]};
    }}

    QProgressBar {{
        min-height: 16px;
        max-height: 16px;
        background-color: {t["progress_bg"]};
        color: {t["text"]};
        border: 1px solid {t["button_border"]};
        border-radius: 5px;
        text-align: center;
        font-size: 10px;
    }}

    QProgressBar::chunk {{
        background-color: {t["progress_chunk"]};
        border-radius: 4px;
    }}

    QSvgWidget#drChart {{
        background-color: rgba(95, 158, 160, 128);
        border-radius: 6px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        border: none;
        width: 10px;
        margin: 4px 2px 4px 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {t["scroll_handle"]};
        min-height: 32px;
        border: none;
        border-radius: 4px;
        margin: 0px 1px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {t["muted"]};
    }}

    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
        border: none;
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        background: transparent;
        border: none;
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        border: none;
        height: 10px;
        margin: 0px 4px 2px 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: {t["scroll_handle"]};
        min-width: 32px;
        border: none;
        border-radius: 4px;
        margin: 1px 0px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {t["muted"]};
    }}

    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
        border: none;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        background: transparent;
        border: none;
        width: 0px;
    }}
    """


# ============================================================
# Microsoft Fluent UI System Icons
# ============================================================


def load_fluent_icon(kind, dark=True, size=TOOLBAR_ICON_SIZE):
    """
    Load one of the bundled official Microsoft Fluent UI System Icons.

    The source SVG stays untouched on disk. Its standard Fluent fill color
    (#212121) is replaced only in memory so the same official artwork is
    readable in both application themes.
    """

    filename = FLUENT_ICON_FILES.get(kind)

    if not filename:
        return QIcon()

    path = FLUENT_ICON_DIR / filename

    if not path.is_file():
        return QIcon()

    try:
        svg = path.read_text(encoding="utf-8")

        theme_color = (
            "#ededed"
            if dark
            else "#1f1f1f"
        )

        svg = svg.replace(
            "#212121",
            theme_color,
        )

        renderer = QSvgRenderer(
            QByteArray(
                svg.encode("utf-8")
            )
        )

        if not renderer.isValid():
            return QIcon()

        pixmap = QPixmap(size, size)
        pixmap.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    except Exception:
        return QIcon()


def _existing_directory(value=None, fallback=None):
    """Return an existing directory, falling back to the current user home."""
    fallback_path = Path(fallback) if fallback else Path.home()
    try:
        candidate = Path(str(value)).expanduser() if value else fallback_path
    except Exception:
        candidate = fallback_path

    if candidate.is_file():
        candidate = candidate.parent
    if candidate.is_dir():
        return candidate
    if fallback_path.is_dir():
        return fallback_path
    return Path.home()


def _resolution_combo(parent, widths, default_value):
    combo = QComboBox(parent)
    for name, width in widths.items():
        combo.addItem(f"{name} ({width} px wide)", name)
    index = combo.findData(default_value)
    combo.setCurrentIndex(index if index >= 0 else combo.findData("High"))
    return combo


# ============================================================
# Export dialogs
# ============================================================


def _add_file_dialog_controls(dialog, rows):
    """Add application-styled controls to a Qt file dialog.

    Native Windows file dialogs cannot host arbitrary Qt widgets, so export
    dialogs deliberately use Qt's own file dialog when format/resolution controls
    need to live in the same window as the file/folder chooser.
    """
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

    panel = QFrame(dialog)
    panel.setObjectName("preferencesGroup")
    grid = QGridLayout(panel)
    grid.setContentsMargins(10, 8, 10, 8)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(7)

    for row_index, (label_text, control) in enumerate(rows):
        label = QLabel(label_text)
        label.setMinimumWidth(120)
        grid.addWidget(label, row_index, 0)
        grid.addWidget(control, row_index, 1)

    layout = dialog.layout()
    if isinstance(layout, QGridLayout):
        layout.addWidget(
            panel,
            layout.rowCount(),
            0,
            1,
            max(1, layout.columnCount()),
        )
    else:
        layout.addWidget(panel)

    dialog.resize(760, 560)
    return panel


def _report_save_dialog(parent, title, default_path, default_format, default_quality):
    default_format = default_format if default_format in SAVE_FORMATS else "PNG"
    default_quality = (
        default_quality
        if default_quality in EXPORT_RESOLUTION_WIDTHS
        else "High"
    )

    info = SAVE_FORMATS[default_format]
    dialog = QFileDialog(parent, title, str(default_path))
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setNameFilters([value["filter"] for value in SAVE_FORMATS.values()])
    dialog.selectNameFilter(info["filter"])
    dialog.setDefaultSuffix(info["extension"].lstrip("."))
    dialog.setLabelText(QFileDialog.DialogLabel.FileType, "Format:")

    quality_combo = _resolution_combo(
        dialog, EXPORT_RESOLUTION_WIDTHS, default_quality
    )
    quality_combo.setToolTip(
        "Controls saved raster resolution. Export never upscales "
        "beyond the rendered source image."
    )
    _add_file_dialog_controls(
        dialog,
        [("Resolution:", quality_combo)],
    )

    def update_default_suffix(selected_filter):
        for format_info in SAVE_FORMATS.values():
            if selected_filter != format_info["filter"]:
                continue

            new_extension = format_info["extension"]
            dialog.setDefaultSuffix(new_extension.lstrip("."))

            # Keep the visible filename in sync with the selected format when
            # it still carries one of our known export extensions. Do not
            # rewrite an arbitrary extension the user typed deliberately.
            selected_files = dialog.selectedFiles()
            if selected_files:
                current = Path(selected_files[0])
                known_extensions = {
                    info["extension"]
                    for info in SAVE_FORMATS.values()
                } | {".jpeg", ".tif"}
                if current.suffix.lower() in known_extensions:
                    dialog.selectFile(str(current.with_suffix(new_extension)))
            break

    dialog.filterSelected.connect(update_default_suffix)
    return dialog, quality_combo


def _report_save_all_dialog(parent, default_directory, default_format, default_quality):
    default_format = default_format if default_format in SAVE_FORMATS else "PNG"
    default_quality = (
        default_quality
        if default_quality in EXPORT_RESOLUTION_WIDTHS
        else "High"
    )

    dialog = QFileDialog(parent, "Save All Tabs", str(default_directory))
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Save All")

    format_combo = QComboBox(dialog)
    format_combo.addItems(list(SAVE_FORMATS.keys()))
    format_combo.setCurrentText(default_format)
    format_combo.setToolTip("Format used for every report saved to the selected folder.")

    quality_combo = _resolution_combo(
        dialog, EXPORT_RESOLUTION_WIDTHS, default_quality
    )
    quality_combo.setToolTip(
        "Controls saved raster resolution. Export never upscales "
        "beyond the rendered source image."
    )

    _add_file_dialog_controls(
        dialog,
        [
            ("Format:", format_combo),
            ("Resolution:", quality_combo),
        ],
    )
    return dialog, format_combo, quality_combo


def _gif_save_dialog(parent, default_path, default_quality, default_duration_seconds):
    default_quality = (
        default_quality
        if default_quality in GIF_RESOLUTION_WIDTHS
        else "High"
    )
    try:
        default_duration_seconds = int(default_duration_seconds)
    except (TypeError, ValueError):
        default_duration_seconds = 3
    default_duration_seconds = max(1, min(30, default_duration_seconds))

    dialog = QFileDialog(parent, "Export Animated GIF", str(default_path))
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setNameFilter("Animated GIF (*.gif)")
    dialog.setDefaultSuffix("gif")

    quality_combo = _resolution_combo(
        dialog, GIF_RESOLUTION_WIDTHS, default_quality
    )
    quality_combo.setToolTip(
        "Standard = 606 px, High = 810 px, Very High = 1080 px wide. "
        "Lower resolution creates substantially smaller GIF files."
    )

    duration_spin = QSpinBox(dialog)
    duration_spin.setRange(1, 30)
    duration_spin.setSingleStep(1)
    duration_spin.setSuffix(" s")
    duration_spin.setValue(default_duration_seconds)
    duration_spin.setToolTip("Time each selected report stays visible in the GIF.")

    _add_file_dialog_controls(
        dialog,
        [
            ("GIF Resolution:", quality_combo),
            ("Frame Duration:", duration_spin),
        ],
    )
    return dialog, quality_combo, duration_spin


# ============================================================
# Preferences
# ============================================================


class PreferencesDialog(QDialog):
    def __init__(self, values, default_app_font, parent=None):
        super().__init__(parent)

        self.values = dict(values)
        self.default_app_font = QFont(default_app_font)
        self.app_font_value = self.values.get("app_font", "")
        self.report_font_value = self.values.get("report_font", "")

        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(680, 420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        # Appearance -------------------------------------------------
        outer.addWidget(self.section_title("Appearance"))
        appearance_group = self.group_frame()
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setContentsMargins(12, 10, 12, 10)
        appearance_layout.setSpacing(9)

        self.appearance_combo = QComboBox()
        self.appearance_combo.addItems(["System", "Light", "Dark"])
        self.appearance_combo.setCurrentText(
            self.values.get("appearance", "System")
        )
        self.appearance_combo.setFixedWidth(160)
        self.appearance_combo.setToolTip(
            "System follows the Windows light/dark setting.\n"
            "Light and Dark force the application appearance."
        )
        appearance_layout.addLayout(
            self.control_row("Theme:", self.appearance_combo)
        )

        app_font_controls = QWidget()
        app_font_layout = QHBoxLayout(app_font_controls)
        app_font_layout.setContentsMargins(0, 0, 0, 0)
        app_font_layout.setSpacing(6)

        self.app_font_label = QLabel()
        self.app_font_label.setObjectName("preferencesValue")
        self.update_app_font_label()

        app_font_choose = QPushButton("Choose...")
        app_font_choose.clicked.connect(self.choose_app_font)
        app_font_choose.setToolTip(
            "Choose the font used by the Windows application interface.\n"
            "Special numeric elements such as the DR badge keep their own font."
        )

        app_font_reset = QPushButton("Default")
        app_font_reset.clicked.connect(self.reset_app_font)

        app_font_layout.addWidget(self.app_font_label, 1)
        app_font_layout.addWidget(app_font_choose)
        app_font_layout.addWidget(app_font_reset)
        appearance_layout.addLayout(
            self.control_row("App Font:", app_font_controls)
        )
        outer.addWidget(appearance_group)

        # Reports ----------------------------------------------------
        outer.addWidget(self.section_title("Reports"))
        reports_group = self.group_frame()
        reports_layout = QVBoxLayout(reports_group)
        reports_layout.setContentsMargins(12, 10, 12, 10)
        reports_layout.setSpacing(9)

        report_font_controls = QWidget()
        report_font_layout = QHBoxLayout(report_font_controls)
        report_font_layout.setContentsMargins(0, 0, 0, 0)
        report_font_layout.setSpacing(6)

        self.report_font_label = QLabel()
        self.report_font_label.setObjectName("preferencesValue")
        self.update_report_font_label()

        report_font_choose = QPushButton("Choose...")
        report_font_choose.clicked.connect(self.choose_report_font)
        report_font_choose.setToolTip(
            "Choose the font used inside newly rendered MasVis reports.\n"
            "Existing result tabs are not re-rendered automatically."
        )

        report_font_reset = QPushButton("Default")
        report_font_reset.clicked.connect(self.reset_report_font)

        report_font_layout.addWidget(self.report_font_label, 1)
        report_font_layout.addWidget(report_font_choose)
        report_font_layout.addWidget(report_font_reset)
        reports_layout.addLayout(
            self.control_row("Report Font:", report_font_controls)
        )

        self.report_theme_combo = QComboBox()
        self.report_theme_combo.addItems(["Light", "Dark"])
        self.report_theme_combo.setCurrentText(
            self.values.get("report_theme", "Light")
        )
        self.report_theme_combo.setFixedWidth(160)
        self.report_theme_combo.setToolTip(
            "Controls the appearance of newly rendered MasVis reports.\n"
            "Light preserves the classic MasVis report palette.\n"
            "Dark uses a dark report background while preserving plot colours.\n"
            "Existing result tabs are not re-rendered automatically."
        )
        reports_layout.addLayout(
            self.control_row("Report Theme:", self.report_theme_combo)
        )

        self.report_quality_combo = QComboBox()
        self.report_quality_combo.addItems(
            ["Standard", "High", "Very High"]
        )
        self.report_quality_combo.setCurrentText(
            self.values.get("report_quality", "High")
        )
        self.report_quality_combo.setFixedWidth(160)
        self.report_quality_combo.setToolTip(
            "Controls the internal resolution of newly rendered detailed reports.\n"
            "Higher quality uses more RAM and takes longer to render.\n"
            "It does not change the audio analysis results."
        )
        reports_layout.addLayout(
            self.control_row("Report Quality:", self.report_quality_combo)
        )
        outer.addWidget(reports_group)

        outer.addStretch(1)

        buttons = QHBoxLayout()
        reset_all = QPushButton("Reset Defaults")
        reset_all.clicked.connect(self.reset_defaults)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        ok = QPushButton("Apply")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)

        buttons.addWidget(reset_all)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        outer.addLayout(buttons)

    @staticmethod
    def section_title(text):
        label = QLabel(text)
        label.setObjectName("preferencesSectionTitle")
        return label

    @staticmethod
    def group_frame():
        frame = QFrame()
        frame.setObjectName("preferencesGroup")
        return frame

    @staticmethod
    def control_row(title, control):
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(title)
        label.setMinimumWidth(180)
        row.addWidget(label)
        row.addWidget(control, 1)
        return row

    def choose_app_font(self):
        initial = qfont_from_string(self.app_font_value)

        if initial is None:
            initial = QFont(self.default_app_font)

        dialog = QFontDialog(
            initial,
            self,
        )
        dialog.setWindowTitle(
            "Choose App Font"
        )

        if (
            dialog.exec()
            == QDialog.DialogCode.Accepted
        ):
            font = dialog.selectedFont()
            self.app_font_value = (
                font.toString()
            )
            self.update_app_font_label()

    def choose_report_font(self):
        initial = qfont_from_string(
            self.report_font_value
        )

        if initial is None:
            initial = QFont()

        dialog = QFontDialog(
            initial,
            self,
        )
        dialog.setWindowTitle(
            "Choose Report Font"
        )

        if (
            dialog.exec()
            == QDialog.DialogCode.Accepted
        ):
            font = dialog.selectedFont()
            self.report_font_value = (
                font.toString()
            )
            self.update_report_font_label()

    def reset_app_font(self):
        self.app_font_value = ""
        self.update_app_font_label()

    def reset_report_font(self):
        self.report_font_value = ""
        self.update_report_font_label()

    def update_app_font_label(self):
        self.app_font_label.setText(
            font_display_name(self.app_font_value)
        )

    def update_report_font_label(self):
        self.report_font_label.setText(
            font_display_name(self.report_font_value)
        )

    def reset_defaults(self):
        self.appearance_combo.setCurrentText("System")
        self.app_font_value = ""
        self.report_font_value = ""
        self.update_app_font_label()
        self.update_report_font_label()
        self.report_theme_combo.setCurrentText("Light")
        self.report_quality_combo.setCurrentText("High")

    def configuration(self):
        return {
            "appearance": self.appearance_combo.currentText(),
            "app_font": self.app_font_value,
            "report_font": self.report_font_value,
            "report_theme": self.report_theme_combo.currentText(),
            "report_quality": self.report_quality_combo.currentText(),
        }


# ============================================================
# Help / Keyboard Shortcuts
# ============================================================


class HelpDialog(QDialog):
    def __init__(self, parent=None, initial_page="Getting Started"):
        super().__init__(parent)

        self.setWindowTitle("Help")
        self.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(
            860,
            640,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        outer.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.navigation = QListWidget()
        self.navigation.setObjectName(
            "helpNavigation"
        )
        self.navigation.setFixedWidth(
            190
        )
        self.navigation.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.pages = [
            (
                "Getting Started",
                self.getting_started_html(),
            ),
            (
                "Reading the Report",
                self.report_html(),
            ),
            (
                "Dynamics Assessment",
                self.dynamics_assessment_html(),
            ),
            (
                "Dynamics Comparison",
                self.dynamics_comparison_html(),
            ),
            (
                "Overview",
                self.overview_html(),
            ),
            (
                "Glossary",
                self.glossary_html(),
            ),
        ]

        self.navigation.setSpacing(
            2
        )

        for title, _html in self.pages:
            item = QListWidgetItem(
                title
            )
            item.setSizeHint(
                QSize(
                    0,
                    38,
                )
            )
            self.navigation.addItem(
                item
            )

        self.help_text = QTextBrowser()
        self.help_text.setObjectName(
            "helpText"
        )
        self.help_text.setOpenExternalLinks(
            False
        )
        self.help_text.setReadOnly(
            True
        )

        self.navigation.currentRowChanged.connect(
            self.show_page
        )

        body.addWidget(
            self.navigation
        )
        body.addWidget(
            self.help_text,
            1,
        )

        outer.addLayout(
            body,
            1,
        )

        footer = QHBoxLayout()
        footer.addStretch(1)

        close_button = QPushButton(
            "Close"
        )
        close_button.setDefault(True)
        close_button.clicked.connect(
            self.accept
        )

        footer.addWidget(
            close_button
        )
        outer.addLayout(
            footer
        )

        initial_row = 0
        for index, (title, _html) in enumerate(self.pages):
            if title == initial_page:
                initial_row = index
                break

        self.navigation.setCurrentRow(
            initial_row
        )

    @staticmethod
    def page(title, body):
        return (
            f"<h2>{title}</h2>"
            f"{body}"
        )

    @classmethod
    def getting_started_html(cls):
        return cls.page(
            "Getting Started",
            """
            <p><b>MasVis for Windows</b> analyzes audio files and turns the
            measurements into visual MasVis reports. It can help you inspect
            loudness, peaks and dynamics, but it does not decide whether a track
            sounds good or reconstruct how it was mastered.</p>

            <h3>A simple workflow</h3>
            <ol>
              <li><b>Open audio.</b> Use <b>Open Files</b> / <b>Ctrl+O</b>, drag &amp; drop files,
                  or use <b>Advanced Open</b> for folders and Overview modes.</li>
              <li><b>Read the report.</b> Each analyzed file gets its own tab. If a term or graph
                  is unfamiliar, start with <b>Reading the Report</b> and the <b>Glossary</b>.</li>
              <li><b>Use the interpretation tools when useful.</b> <b>Dynamics Assessment</b>
                  summarizes level-maximization evidence for one track. <b>Dynamics Comparison</b>
                  compares two versions of substantially the same musical material.</li>
              <li><b>Save or compare.</b> Save the current report, save all open reports,
                  place reports side-by-side, or export selected tabs as an animated GIF.</li>
            </ol>

            <h3>Buttons around the report</h3>
            <ul>
              <li>The <b>DR badge</b> opens channel DR values and the Dynamic Range chart.</li>
              <li><b>Dynamics Assessment</b> explains how strongly the current waveform shows
                  signatures associated with level maximization.</li>
              <li><b>Compare</b> opens side-by-side comparison, GIF export and Dynamics Comparison.</li>
              <li><b>Play</b> opens the audio file from the current detailed tab in the
                  <b>default audio player configured in Windows</b>. MasVis does not contain an
                  audio player of its own. Play is disabled when no detailed file tab is active.</li>
              <li><b>File Information</b> shows technical properties, metadata and analysis details.</li>
              <li>The floating controls zoom the current report or fit it to the window.</li>
            </ul>

            <h3>Saving and Preferences</h3>
            <p><b>Save</b> and <b>Save All</b> ask for format and export resolution at the time
            you save. GIF export asks for its resolution and frame duration in the same way.
            The last-used folders and export choices are remembered for convenience.</p>

            <p><b>Preferences</b> contains settings that affect the application itself or how
            <i>new reports are rendered</i>, such as theme, fonts and Report Quality. Report
            Quality is different from export Resolution: it controls the source report created
            during analysis, while export Resolution controls the size of the saved copy.</p>

            <p><i>Existing tabs are already-rendered images. Changing Report Font, Report Theme
            or Report Quality affects newly analyzed reports and does not regenerate tabs that
            are already open.</i></p>
            """,
        )
    @classmethod
    def report_html(cls):
        return cls.page(
            "Reading the Report",
            """
            <p>The detailed report shows several views of the same track. The safest way to
            read it is to look for a <b>pattern across multiple measurements</b> rather than
            treating one number or one graph as a verdict. Higher or lower is not automatically
            better, and none of these measurements is a sound-quality score.</p>

            <h3>Header measurements</h3>
            <p><b>DR</b> is the classic MasVis/TT-style dynamic-range value. <b>LUFS/LU</b>
            describes overall loudness, <b>LRA</b> how widely loudness varies across the track,
            <b>PLR</b> the distance between True Peak and Integrated Loudness, and <b>Crest</b>
            the relationship between peak and RMS level. The Glossary explains each term in
            more detail.</p>

            <h3>Channel waveforms</h3>
            <p>The first plots show the waveform of each channel. The labels include crest
            factor, RMS level, sample peak and True Peak. Sample Peak is the highest stored
            digital sample; True Peak estimates peaks that can appear between samples when the
            waveform is reconstructed.</p>

            <h3>Loudest part</h3>
            <p>MasVis automatically zooms into a short, very strong section of the track.
            Repeatedly flattened or tightly constrained peaks can make clipping or strong
            limiting easier to recognize, but the picture should be read together with the
            other measurements.</p>

            <h3>Normalized average spectrum</h3>
            <p>Shows the average frequency balance after removing the simple overall level
            difference. This can be useful when comparing different releases of the same
            recording because obvious tonal/EQ differences become easier to spot.</p>

            <h3>Allpassed crest factor</h3>
            <p>Compares the measured crest factor with the crest factor after phase-only
            allpass filtering. A large recovery can be a sign that peak structure has been
            strongly altered, but phase and source differences can also affect it.</p>

            <h3>Histogram</h3>
            <p>Shows how often sample values occur. Strong concentrations near the level limits
            can support evidence of clipping or heavy limiting.</p>

            <h3>Peak vs. RMS</h3>
            <p>Each point represents a short section of the track. Sections with high RMS and
            little room above them for peaks indicate a dense signal. The overall shape is more
            useful than any single dot.</p>

            <h3>Short-term crest factor</h3>
            <p>Tracks peak-to-average contrast over time. It helps show whether louder sections
            retain strong peaks or become increasingly dense.</p>

            <h3>EBU R128 short-term loudness</h3>
            <p>Shows how perceived loudness changes through the track, together with Short-Term
            PLR. This is useful for seeing musical rises and falls that a single whole-track
            value cannot show.</p>

            <h3>Where to go next</h3>
            <p>Use <b>Dynamics Assessment</b> when you want a cautious summary of
            level-maximization evidence in one file. Use <b>Dynamics Comparison</b> when you
            have two versions of the same material and want to know whether their measured DR,
            loudness development and peak structure tell the same story.</p>
            """,
        )
    @classmethod
    def dynamics_assessment_html(cls):
        return cls.page(
            "Dynamics Assessment",
            """
            <p><b>Dynamics Assessment</b> asks a simple question: <i>how strongly does this
            waveform contain measurable signatures commonly associated with pushing a master
            toward higher average loudness?</i></p>

            <p>It combines several measurements into a <b>Level Maximization Evidence</b> score
            from 0 to 100. The score is <b>not a probability and not a sound-quality grade</b>.
            For example, 85/100 does not mean an 85% chance of a "bad master". It means that
            several measurable indicators point strongly in the same direction.</p>

            <h3>Score bands</h3>
            <ul>
              <li><b>Low (0-19)</b> - little direct evidence in the current waveform.</li>
              <li><b>Mild (20-39)</b> - some signatures are present, but overall evidence is limited.</li>
              <li><b>Moderate (40-59)</b> - several signatures are present, with mixed evidence.</li>
              <li><b>High (60-79)</b> - strong combined evidence of level maximization.</li>
              <li><b>Very High (80-100)</b> - very strong combined evidence of aggressive level maximization.</li>
            </ul>

            <h3>What contributes to the score?</h3>
            <p>You do not need to memorize the weights, but they are shown here so the score is
            transparent rather than a black box:</p>
            <ul>
              <li><b>Allpass crest-factor recovery - up to 35 points.</b> Large recovery can indicate that peak/crest structure has been strongly constrained.</li>
              <li><b>Peak-to-Loudness Ratio (PLR) - up to 25 points.</b> Low PLR means little peak margin relative to overall loudness.</li>
              <li><b>Short-term density - up to 15 points.</b> Looks at how dense the signal remains across short sections of the track.</li>
              <li><b>Loud-section crest factor - up to 15 points.</b> Checks peak-to-average contrast in the loudest one-second sections.</li>
              <li><b>Integrated loudness - up to 10 points.</b> Very high loudness can strengthen other evidence, but cannot dominate the result by itself.</li>
            </ul>

            <p><b>DR and LRA are context only and do not directly add points.</b> This is
            deliberate: a high TT-style DR value is not automatically proof of more musical
            dynamics, and a low value alone does not prove destructive mastering.</p>

            <h3>How to read the result window</h3>
            <p><b>Evidence</b> lists measurements that push the score upward.
            <b>Counter-evidence</b> lists measurements that make a strong level-maximization
            interpretation less convincing. Two files can therefore have similar scores for
            different reasons.</p>

            <p><b>Measurement confidence</b> mainly tells you whether the track is long enough
            for distribution-based measurements to be useful. It is not statistical confidence
            that the mastering history has been identified.</p>

            <h3>Important limitations</h3>
            <ul>
              <li>The assessment describes the <b>current waveform</b>; it cannot reconstruct the original mastering process.</li>
              <li>A vinyl rip or other analog/captured source can change peaks, phase and EQ after mastering.</li>
              <li>Different media, filtering and phase changes can alter DR/crest measurements without restoring lost loudness dynamics.</li>
              <li>The score does not judge artistic intent, genre or whether you will prefer the sound.</li>
              <li>To compare two editions directly, use <b>Dynamics Comparison</b>.</li>
            </ul>
            """,
        )
    @classmethod
    def dynamics_comparison_html(cls):
        return cls.page(
            "Dynamics Comparison",
            """
            <p><b>Dynamics Comparison</b> is for two versions of substantially the same musical
            material. Its goal is to separate three things that are easy to mix together:
            <b>measured DR</b>, <b>loudness dynamics over time</b>, and
            <b>peak/crest structure</b>.</p>

            <p><b>The simple question is:</b> <i>if two versions of the same music measure
            differently, what is really different - mainly their level, their loudness dynamics
            over time, their peak/crest structure, or some combination of those?</i></p>

            <h3>What the program does</h3>
            <ol>
              <li><b>Aligns the files</b> so the same musical moments line up. A small constant
                  speed drift is allowed for captures such as vinyl playback.</li>
              <li><b>Matches their typical loudness level</b> so "this one is simply louder"
                  does not masquerade as a dynamics difference.</li>
              <li><b>Compares the aligned loudness curves</b> and separately measures changes in
                  local peak/crest structure.</li>
            </ol>

            <p>If the files cannot be aligned reliably enough, the result is
            <b>Inconclusive</b>. MasVis for Windows deliberately refuses to produce a mastering-
            dynamics verdict for a wrong song, substantially different edit or unreliable match.</p>

            <h3>Loudness Curve Similarity</h3>
            <p>This is the Pearson correlation of the aligned EBU R128 Short-Term loudness
            curves, displayed as a percentage. A high value means the two versions tend to get
            louder and quieter at the same musical moments. It does <b>not</b> mean that their
            amount of loudness variation or their peak structure is identical.</p>

            <h3>Loudness Dynamics Similarity (LDS)</h3>
            <p>LDS is an explainable <b>0-100 point score</b>, not a percentage or probability.
            Version 1 combines:</p>
            <ul>
              <li><b>55%</b> similarity of the aligned Short-Term curve shape;</li>
              <li><b>30%</b> how small the remaining loudness differences are after level matching;</li>
              <li><b>15%</b> similarity of the robust Short-Term loudness span.</li>
            </ul>

            <p>This is why Loudness Curve Similarity can be extremely high while LDS is lower:
            two curves can rise and fall together but one version can make those rises and falls
            noticeably wider or narrower.</p>

            <h3>Loudness Dynamics Advantage</h3>
            <p>Shows whether Version A or B has the wider aligned Short-Term loudness span, with
            EBU LRA used as supporting evidence. The result can also be None detected, Mixed or
            Inconclusive. DR and PLR deliberately do not choose the winner, so a peak-based DR
            increase is not automatically counted as more loudness dynamics.</p>

            <h3>Peak Structure Difference</h3>
            <p>This separate 0-100 point score describes how strongly local peak and crest
            behaviour differs after alignment and level matching. It is a <b>difference</b>
            measure, not a quality score. 100/100 means the defined scale reached its maximum;
            it does not mean that literally every transient is different.</p>

            <h3>Level Difference</h3>
            <p>The typical loudness offset between the two aligned versions is shown separately.
            Pure gain by itself does not change DR, PLR or crest factor, so a quieter file does
            not automatically receive credit for having more dynamics.</p>

            <h3>A practical way to read the result</h3>
            <ol>
              <li>Check that <b>Alignment</b> is Reliable.</li>
              <li>Look at the normal <b>DR</b> values and the displayed level difference.</li>
              <li>Use <b>LDS</b> and <b>Loudness Dynamics Advantage</b> for the broader loudness
                  development over time.</li>
              <li>Use <b>Peak Structure Difference</b> and PLR as a separate view of peaks and
                  peak headroom.</li>
              <li>Read the conclusion as a summary of those measurements, not as a claim about
                  which release sounds better.</li>
            </ol>

            <h3>Typical conclusions</h3>
            <ul>
              <li><b>Primarily a level shift</b> - level differs while the measured dynamics remain essentially the same.</li>
              <li><b>Higher measured DR, but little loudness-dynamics advantage</b> - DR differs strongly, while the aligned Short-Term loudness development remains very similar.</li>
              <li><b>Higher measured DR is corroborated</b> - the higher-DR version also shows a wider aligned Short-Term loudness range.</li>
              <li><b>Measured DR and loudness dynamics disagree</b> - peak-based DR and aligned Short-Term loudness dynamics point in different directions.</li>
              <li><b>Mixed evidence</b> - the available measurements do not support one simple direction.</li>
            </ul>

            <h3>Important limitations</h3>
            <ul>
              <li>Use the feature only for two versions of substantially the same musical content.</li>
              <li>The comparison measures the supplied waveforms; it does not reconstruct mastering history.</li>
              <li>EQ, filtering, phase changes and analog playback/capture can alter peak structure without a comparable change in Short-Term loudness dynamics.</li>
              <li>The result is not a subjective sound-quality rating and does not judge artistic intent.</li>
            </ul>
            """,
        )
    @classmethod
    def overview_html(cls):
        return cls.page(
            "Overview",
            """
            <p><b>Overview</b> is a compact way to scan many tracks at once, for example an
            album or several folders. Each row summarizes one file instead of showing every
            graph from the full detailed report.</p>

            <p>Channel waveforms are superimposed:</p>
            <ul>
              <li>Left channel: <b>blue</b></li>
              <li>Right channel: <b>red</b></li>
              <li>Overlapping content: <b>black</b></li>
            </ul>

            <p>The information beside each row includes <b>DR</b>, <b>Peak</b>,
            <b>Crest</b> and Integrated Loudness.</p>

            <h3>Advanced Open modes</h3>
            <ul>
              <li><b>Off</b> - create a normal detailed tab for each file.</li>
              <li><b>All files (flat)</b> - place all selected files in one Overview tab.</li>
              <li><b>By folder (dir)</b> - create one Overview tab for each containing folder.</li>
            </ul>

            <p>Overview tabs support zoom, Save, Compare and GIF export. Because one Overview
            tab can represent several audio files, <b>Play</b>, File Information, the DR badge
            and Dynamics Assessment are available only on individual detailed report tabs.</p>
            """,
        )
    @classmethod
    def glossary_html(cls):
        return cls.page(
            "Glossary",
            """
            <h3>DR (Dynamic Range)</h3>
            <p>The MasVis/TT-style dynamic-range metric. It mainly describes the
            relationship between loud RMS blocks and peaks. It is useful when
            comparing similar digital masters, but it is not a universal measure
            of musical dynamics or sound quality.</p>

            <h3>LUFS / Integrated Loudness (LUFS-I)</h3>
            <p>Loudness Units relative to Full Scale. Integrated LUFS describes
            the perceived loudness of the complete track according to EBU R128 /
            ITU-R BS.1770-style measurement.</p>

            <h3>LU</h3>
            <p>A relative Loudness Unit. In Advanced Open, LU display is shown
            relative to the -23 LUFS reference used by EBU R128.</p>

            <h3>Momentary Loudness</h3>
            <p>A short-window loudness measurement that follows rapid level
            changes. Dynamics Comparison uses the aligned Momentary trajectory
            for timing and level-reference work.</p>

            <h3>Short-Term Loudness</h3>
            <p>A longer-window loudness measurement that follows the broader
            loudness development of the music. It is the main trajectory used by
            Loudness Dynamics Similarity and Loudness Dynamics Advantage.</p>

            <h3>LRA (Loudness Range)</h3>
            <p>Describes how widely loudness varies across the program. It is a
            separate EBU R128 measurement and is used as supporting evidence in
            Dynamics Comparison.</p>

            <h3>PLR (Peak-to-Loudness Ratio)</h3>
            <p>The distance between True Peak and Integrated Loudness. It
            describes peak headroom relative to overall loudness and is kept
            separate from Short-Term loudness dynamics.</p>

            <h3>Crest factor</h3>
            <p>The difference between peak and RMS level. Higher crest factor
            means peaks rise farther above the average signal level.</p>

            <h3>Sample Peak</h3>
            <p>The highest stored digital sample value in the file. It can differ
            from True Peak because reconstructed playback can create a slightly
            higher peak between samples.</p>

            <h3>True Peak / dBTP</h3>
            <p>True Peak estimates the maximum reconstructed waveform peak,
            including peaks that can occur between stored digital samples. dBTP
            is the unit used for that reconstructed peak level.</p>

            <h3>Headroom</h3>
            <p>The available level space between the current signal and a peak
            limit. More headroom gives peaks more room to rise; it is not by
            itself a measure of musical quality.</p>

            <h3>dBFS</h3>
            <p>Decibels relative to digital full scale. 0 dBFS is the maximum
            sample level representable by the digital scale; ordinary sample
            peaks are normally at or below it.</p>

            <h3>RMS</h3>
            <p>Root Mean Square. A measure related to average signal power over a
            period of time. MasVis uses RMS measurements in several classic
            dynamics and crest calculations.</p>

            <h3>Loudness Dynamics Similarity (LDS)</h3>
            <p>An explainable 0..100 <b>point score</b> for two reliably aligned
            versions. It combines Short-Term trajectory correlation, residual
            differences after level matching and the difference in robust
            Short-Term loudness span. It is not a percentage, probability or
            sound-quality rating.</p>

            <h3>Loudness Curve Similarity</h3>
            <p>The actual Pearson correlation of the aligned, level-matched
            Short-Term loudness trajectories, displayed as a percentage. A high
            value means the curves tend to rise and fall together; it does not
            mean their dynamic range or peak structure is identical.</p>

            <h3>Loudness Dynamics Advantage</h3>
            <p>Indicates whether Version A or B shows the wider aligned Short-Term
            loudness span, with EBU LRA used as supporting evidence. It does not
            mean that one version necessarily sounds better.</p>

            <h3>Peak Structure Difference</h3>
            <p>An explainable 0..100 point score describing how strongly local
            peak and crest structure differs after time alignment and level
            matching. 100/100 means the score reached the top of its defined
            scale; it does not mean literally 100% of all transients differ.</p>

            <h3>Level Difference / Level Matching</h3>
            <p>Dynamics Comparison estimates the typical loudness offset between
            aligned versions and removes that offset before judging their
            loudness-development similarity. A simple gain change therefore
            does not become a false dynamics advantage.</p>

            <h3>Alignment</h3>
            <p>The process of matching the same musical moments in two versions
            before comparing them. MasVis for Windows can also model a small
            constant playback-speed drift, which is useful for analog or vinyl
            captures. Unreliable alignment produces an Inconclusive result.</p>

            <h3>Pearson correlation</h3>
            <p>A mathematical measure of how closely two curves vary together.
            Dynamics Comparison uses it for Loudness Curve Similarity after
            alignment and level matching. Correlation describes curve shape, not
            absolute loudness or subjective quality.</p>

            <h3>Gain / level change</h3>
            <p>A simple gain change turns the whole signal up or down by the same
            amount. By itself it changes absolute loudness and peak level, but it
            does not change DR, PLR or crest factor.</p>

            <h3>Master / mastering</h3>
            <p>Mastering is the final processing and preparation stage for a
            release. Different releases of the same recording can use different
            masters. MasVis can compare the resulting audio, but it cannot prove
            the exact processing history that created it.</p>

            <h3>Transient</h3>
            <p>A short, fast-changing sound event such as a drum hit or other
            attack. Compression, limiting, clipping, filtering and playback
            chains can all change transient peak shape.</p>

            <h3>EBU R128</h3>
            <p>A broadcast loudness measurement standard used here for Integrated,
            Momentary and Short-Term loudness and for Loudness Range (LRA).</p>

            <h3>EQ / phase</h3>
            <p><b>EQ</b> changes frequency balance. <b>Phase</b> describes timing
            relationships between frequency components. Either can change waveform
            and peak shape even when the musical performance itself is unchanged.</p>

            <h3>Dynamic-range compression</h3>
            <p>Audio processing that reduces level differences between louder and
            quieter signal portions. This is different from data compression such
            as FLAC, MP3 or Opus.</p>

            <h3>Limiting</h3>
            <p>A strong form of dynamics control used to restrain peaks, often so
            the overall signal can be raised further. Its effect can be visible in
            crest, PLR, DR and peak-structure measurements.</p>

            <h3>Clipping</h3>
            <p>Occurs when waveform peaks exceed an available level boundary and
            are truncated or otherwise constrained. Clipping can alter peak shape
            and create distortion.</p>

            <h3>Loudness War / Level Maximization</h3>
            <p>Terms commonly used for mastering practices aimed at increasing
            average playback loudness, often with compression, limiting or
            clipping. A louder master is not automatically less dynamic; the
            relevant question is what processing changed besides simple gain.</p>

            <h3>Allpass filter</h3>
            <p>A filter that changes phase relationships without intentionally
            changing the frequency magnitude response. MasVis uses this behavior
            to examine peak structure.</p>

            <h3>Vinyl / needledrop</h3>
            <p>A digital capture of vinyl passes through the cutting/playback
            chain, cartridge, phono stage and analog-to-digital conversion. Those
            processes can change EQ, phase and reconstructed peaks, so a higher
            TT-style DR value from a vinyl capture alone does not prove that its
            source master had greater musical loudness dynamics.</p>

            <h3>Checksum (energy)</h3>
            <p>The MasVis report includes an energy-based checksum that helps
            identify whether two analyses originated from equivalent audio data.</p>
            """,
        )

    def show_page(self, row):
        if row < 0 or row >= len(
            self.pages
        ):
            return

        _title, html = self.pages[
            row
        ]

        self.help_text.setHtml(
            html
        )


class KeyboardShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Keyboard Shortcuts"
        )
        self.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(
            840,
            470,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        outer.setSpacing(10)

        window_rows = [
            ("Help Manual", "F1"),
            ("Keyboard Shortcuts", "Ctrl+?"),
            ("Preferences", "Ctrl+,"),
            ("Fullscreen / Restore", "F11"),
            ("Exit Fullscreen", "Esc"),
            ("Quit", "Ctrl+Q"),
        ]

        file_rows = [
            ("Open Files", "Ctrl+O"),
            ("Advanced Open / Overview", "Shift+O"),
            ("File Information", "Ctrl+I"),
        ]

        tab_rows = [
            ("Close Current Tab", "Ctrl+W"),
            ("Next Tab", "Ctrl+Tab"),
            ("Previous Tab", "Ctrl+Shift+Tab"),
            ("Save Current Tab", "Ctrl+S"),
            ("Save All Tabs", "Ctrl+Shift+S"),
            ("Compare Tabs", "Ctrl+G"),
            ("Zoom In", "Ctrl++"),
            ("Zoom Out", "Ctrl+-"),
            ("Original Size (1:1)", "Ctrl+0"),
        ]

        body = QHBoxLayout()
        body.setSpacing(12)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)

        left_column.addWidget(
            self.section_title(
                "Window Actions"
            )
        )
        left_column.addWidget(
            self.group_frame(
                window_rows
            )
        )
        left_column.addWidget(
            self.section_title(
                "File Actions"
            )
        )
        left_column.addWidget(
            self.group_frame(
                file_rows
            )
        )
        left_column.addStretch(1)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.addWidget(
            self.section_title(
                "Tab Actions"
            )
        )
        right_column.addWidget(
            self.group_frame(
                tab_rows
            )
        )
        right_column.addStretch(1)

        body.addLayout(
            left_column,
            1,
        )
        body.addLayout(
            right_column,
            1,
        )

        outer.addLayout(
            body,
            1,
        )

        footer = QHBoxLayout()
        footer.addStretch(1)

        close_button = QPushButton(
            "Close"
        )
        close_button.setDefault(True)
        close_button.clicked.connect(
            self.accept
        )

        footer.addWidget(
            close_button
        )
        outer.addLayout(
            footer
        )

    @staticmethod
    def section_title(text):
        label = QLabel(text)
        label.setObjectName(
            "shortcutsSectionTitle"
        )
        return label

    @staticmethod
    def group_frame(rows):
        frame = QFrame()
        frame.setObjectName(
            "shortcutsGroup"
        )

        grid = QGridLayout(frame)
        grid.setContentsMargins(
            12,
            9,
            12,
            9,
        )
        grid.setHorizontalSpacing(
            10
        )
        grid.setVerticalSpacing(
            7
        )
        grid.setColumnStretch(
            0,
            1,
        )
        grid.setColumnMinimumWidth(
            1,
            128,
        )

        for index, (
            action,
            key,
        ) in enumerate(rows):
            action_label = QLabel(
                action
            )
            action_label.setObjectName(
                "shortcutAction"
            )

            key_label = QLabel(
                key
            )
            key_label.setObjectName(
                "shortcutKey"
            )
            key_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            key_label.setMinimumWidth(
                128
            )

            grid.addWidget(
                action_label,
                index,
                0,
            )
            grid.addWidget(
                key_label,
                index,
                1,
            )

        return frame


# ============================================================
# About
# ============================================================


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            f"About {APP_NAME}"
        )
        self.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(
            620,
            520,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            22,
            20,
            22,
            18,
        )
        outer.setSpacing(12)

        # Header -----------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(16)

        icon_holder = QWidget()
        icon_holder.setFixedSize(
            78,
            78,
        )

        if APP_ICON.is_file():
            icon = QLabel(icon_holder)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setPixmap(
                QPixmap(str(APP_ICON)).scaled(
                    72,
                    72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            icon.setGeometry(
                3,
                3,
                72,
                72,
            )
        else:
            fallback = QLabel(
                "MV",
                icon_holder,
            )
            fallback.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            fallback.setGeometry(
                3,
                3,
                72,
                72,
            )

        title_column = QVBoxLayout()
        title_column.setContentsMargins(
            0,
            7,
            0,
            0,
        )
        title_column.setSpacing(4)

        title = QLabel(
            APP_NAME
        )
        title.setObjectName(
            "aboutTitle"
        )

        version = QLabel(
            APP_VERSION
        )
        version.setObjectName(
            "aboutVersion"
        )

        description = QLabel(
            "Audio loudness, dynamics and mastering analysis "
            "with a native Windows interface."
        )
        description.setObjectName(
            "aboutDescription"
        )
        description.setWordWrap(
            True
        )

        title_column.addWidget(
            title
        )
        title_column.addWidget(
            version
        )
        title_column.addWidget(
            description
        )
        title_column.addStretch(1)

        header.addWidget(
            icon_holder
        )
        header.addLayout(
            title_column,
            1,
        )

        outer.addLayout(
            header
        )

        # Project lineage -------------------------------------------
        lineage = self.group_frame()
        lineage_layout = QVBoxLayout(
            lineage
        )
        lineage_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        lineage_layout.setSpacing(5)

        lineage_title = QLabel(
            "Project"
        )
        lineage_title.setObjectName(
            "aboutSectionTitle"
        )

        lineage_text = QLabel(
            "MasVis for Windows is an independent Windows-native fork of "
            "MasVisGtk by ITProjects. MasVisGtk builds on PyMasVis by "
            "Joakim Fors, a Python reimplementation of the original "
            "MasVis.\n\n"
            "Upstream: MasVisGtk — ITProjects\n"
            "Python reimplementation: PyMasVis — Joakim Fors\n"
            "Original lineage: MasVis"
        )
        lineage_text.setWordWrap(
            True
        )
        lineage_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        lineage_layout.addWidget(
            lineage_title
        )
        lineage_layout.addWidget(
            lineage_text
        )

        outer.addWidget(
            lineage
        )

        # Technical basis -------------------------------------------
        tech = self.group_frame()
        tech_layout = QVBoxLayout(
            tech
        )
        tech_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        tech_layout.setSpacing(5)

        tech_title = QLabel(
            "Technical basis"
        )
        tech_title.setObjectName(
            "aboutSectionTitle"
        )

        tech_text = QLabel(
            "Interface: PySide6 / Qt\n"
            "Audio decoding: FFmpeg\n"
            "Analysis basis: MasVisGtk / PyMasVis, NumPy and SciPy\n"
            "Report rendering: Matplotlib"
        )
        tech_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        tech_layout.addWidget(
            tech_title
        )
        tech_layout.addWidget(
            tech_text
        )

        outer.addWidget(
            tech
        )

        # License ----------------------------------------------------
        license_group = self.group_frame()
        license_layout = QVBoxLayout(
            license_group
        )
        license_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )
        license_layout.setSpacing(5)

        license_title = QLabel(
            "License"
        )
        license_title.setObjectName(
            "aboutSectionTitle"
        )

        license_text = QLabel(
            "GNU General Public License, version 3 or later "
            "(GPL-3.0-or-later).\n"
            "Windows fork modifications: Copyright (C) 2026 adventureFAN.\n"
            "Upstream copyright and license notices are preserved."
        )
        license_text.setWordWrap(
            True
        )
        license_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        independent_note = QLabel(
            "This fork is developed independently and is not an official "
            "MasVisGtk upstream release."
        )
        independent_note.setObjectName(
            "aboutMuted"
        )
        independent_note.setWordWrap(
            True
        )

        license_layout.addWidget(
            license_title
        )
        license_layout.addWidget(
            license_text
        )
        license_layout.addWidget(
            independent_note
        )

        outer.addWidget(
            license_group
        )

        outer.addStretch(1)

        # Footer -----------------------------------------------------
        footer = QHBoxLayout()
        footer.setSpacing(8)

        project_button = QPushButton(
            "Project on GitHub"
        )
        project_button.setToolTip(
            "Open the MasVis for Windows project on GitHub."
        )
        project_button.clicked.connect(
            self.open_project
        )

        upstream_button = QPushButton(
            "Upstream Project"
        )
        upstream_button.setToolTip(
            "Open the original MasVisGtk project on GitHub."
        )
        upstream_button.clicked.connect(
            self.open_upstream
        )

        close_button = QPushButton(
            "Close"
        )
        close_button.setDefault(
            True
        )
        close_button.clicked.connect(
            self.accept
        )

        footer.addWidget(
            project_button
        )
        footer.addWidget(
            upstream_button
        )
        footer.addStretch(1)
        footer.addWidget(
            close_button
        )

        outer.addLayout(
            footer
        )

    @staticmethod
    def group_frame():
        frame = QFrame()
        frame.setObjectName(
            "aboutGroup"
        )
        return frame

    def open_project(self):
        QDesktopServices.openUrl(
            QUrl(
                PROJECT_URL
            )
        )

    def open_upstream(self):
        QDesktopServices.openUrl(
            QUrl(
                UPSTREAM_PROJECT_URL
            )
        )


# ============================================================
# File Information
# ============================================================


class FileInformationDialog(QDialog):
    def __init__(self, report, parent=None):
        super().__init__(parent)

        self.report = report
        self.result = report.result
        self.track = self.result["track"]
        self.metadata = self.track["metadata"]

        path = Path(self.result["path"])

        self.setWindowTitle(
            f"File Information - {path.name}"
        )
        self.setWindowModality(
            Qt.WindowModality.WindowModal
        )
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(
            680,
            650,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        outer.setSpacing(10)

        title = QLabel(path.name)
        title.setObjectName(
            "fileInfoTitle"
        )
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        subtitle = QLabel(str(path))
        subtitle.setObjectName(
            "fileInfoSubtitle"
        )
        subtitle.setWordWrap(True)
        subtitle.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        outer.addWidget(title)
        outer.addWidget(subtitle)

        # File -------------------------------------------------------
        outer.addWidget(
            self.section_title("File")
        )

        file_rows = [
            (
                "Name",
                path.name,
            ),
            (
                "Location",
                str(path.parent),
            ),
            (
                "Size",
                self.file_size_text(),
            ),
        ]

        outer.addWidget(
            self.info_group(file_rows)
        )

        # Audio ------------------------------------------------------
        outer.addWidget(
            self.section_title("Audio")
        )

        audio_rows = [
            (
                "Format",
                self.format_text(),
            ),
            (
                "Encoding",
                self.value_or_unknown(
                    self.metadata.get(
                        "encoding"
                    )
                ),
            ),
            (
                "Channels",
                str(
                    self.track.get(
                        "channels",
                        "Unknown",
                    )
                ),
            ),
            (
                "Channel layout",
                self.channel_layout_text(),
            ),
            (
                "Bit depth",
                self.bit_depth_text(),
            ),
            (
                "Sample rate",
                self.sample_rate_text(),
            ),
            (
                "Bitrate",
                self.bitrate_text(),
            ),
            (
                "Duration",
                format_duration(
                    float(
                        self.track.get(
                            "duration",
                            0.0,
                        )
                    )
                ),
            ),
        ]

        outer.addWidget(
            self.info_group(audio_rows)
        )

        # Metadata ---------------------------------------------------
        outer.addWidget(
            self.section_title("Metadata")
        )

        metadata_rows = [
            (
                "Artist",
                self.value_or_unknown(
                    self.metadata.get(
                        "artist"
                    )
                ),
            ),
            (
                "Title",
                self.value_or_unknown(
                    self.metadata.get(
                        "title"
                    )
                ),
            ),
            (
                "Album",
                self.value_or_unknown(
                    self.metadata.get(
                        "album"
                    )
                ),
            ),
            (
                "Track",
                self.value_or_unknown(
                    self.metadata.get(
                        "track"
                    )
                ),
            ),
            (
                "Date",
                self.value_or_unknown(
                    self.metadata.get(
                        "date"
                    )
                ),
            ),
        ]

        outer.addWidget(
            self.info_group(metadata_rows)
        )

        # Analysis ---------------------------------------------------
        outer.addWidget(
            self.section_title("Analysis")
        )

        r128_unit = self.result.get(
            "r128_unit",
            "LUFS",
        )

        if r128_unit == "LU":
            loudness_value = (
                float(
                    self.result["lufs"]
                )
                + 23.0
            )
            loudness_text = (
                f"{loudness_value:.2f} LU"
            )
        else:
            loudness_text = (
                f"{float(self.result['lufs']):.2f} LUFS"
            )

        analysis_rows = [
            (
                "Dynamic Range",
                f"DR {float(self.result['dr']):.1f}",
            ),
            (
                "Integrated loudness",
                loudness_text,
            ),
            (
                "Loudness Range",
                f"{float(self.result['lra']):.2f} LU",
            ),
            (
                "Peak-to-Loudness Ratio",
                f"{float(self.result['plr']):.2f} LU",
            ),
            (
                "Crest factor",
                f"{float(self.result['crest']):.2f} dB",
            ),
            (
                "True Peak",
                f"{float(self.result['true_peak']):.2f} dBTP",
            ),
        ]

        outer.addWidget(
            self.info_group(analysis_rows)
        )

        outer.addStretch(1)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.copied_label = QLabel("")
        self.copied_label.setObjectName(
            "fileInfoCopied"
        )

        copy_button = QPushButton(
            "Copy Details"
        )
        copy_button.setToolTip(
            "Copy all displayed file, metadata and analysis details\n"
            "to the Windows clipboard."
        )
        copy_button.clicked.connect(
            self.copy_details
        )

        close_button = QPushButton(
            "Close"
        )
        close_button.setDefault(True)
        close_button.clicked.connect(
            self.accept
        )

        footer.addWidget(
            copy_button
        )
        footer.addWidget(
            self.copied_label
        )
        footer.addStretch(1)
        footer.addWidget(
            close_button
        )

        outer.addLayout(
            footer
        )

    @staticmethod
    def section_title(text):
        label = QLabel(text)
        label.setObjectName(
            "fileInfoSectionTitle"
        )
        return label

    @staticmethod
    def value_or_unknown(value):
        if value is None:
            return "Unknown"

        value = str(value).strip()

        return (
            value
            if value
            else "Unknown"
        )

    def info_group(self, rows):
        frame = QFrame()
        frame.setObjectName(
            "fileInfoGroup"
        )

        grid = QGridLayout(frame)
        grid.setContentsMargins(
            12,
            9,
            12,
            9,
        )
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        grid.setColumnMinimumWidth(
            0,
            165,
        )
        grid.setColumnStretch(
            1,
            1,
        )

        for row_index, (
            key,
            value,
        ) in enumerate(rows):
            key_label = QLabel(
                f"{key}:"
            )
            key_label.setObjectName(
                "fileInfoKey"
            )
            key_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
            )

            value_label = QLabel(
                str(value)
            )
            value_label.setObjectName(
                "fileInfoValue"
            )
            value_label.setWordWrap(
                True
            )
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            grid.addWidget(
                key_label,
                row_index,
                0,
            )
            grid.addWidget(
                value_label,
                row_index,
                1,
            )

        return frame

    def file_size_text(self):
        size = int(
            self.metadata.get(
                "size"
            )
            or 0
        )

        if size <= 0:
            return "Unknown"

        return (
            f"{size / (1024 * 1024):.2f} MB"
            f" ({size:,} bytes)"
        )

    def format_text(self):
        value = self.track.get(
            "format"
        )

        if not value:
            value = Path(
                self.result["path"]
            ).suffix.lstrip(".")

        return (
            str(value).upper()
            if value
            else "Unknown"
        )

    def channel_layout_text(self):
        layout = self.result.get(
            "channel_layout"
        )

        if not layout:
            channels = int(
                self.track.get(
                    "channels",
                    0,
                )
                or 0
            )

            if channels == 1:
                return "Mono"

            if channels == 2:
                return "Stereo"

            return "Unknown"

        normalized = str(
            layout
        ).replace(
            "_",
            " ",
        )

        return normalized[:1].upper() + normalized[1:]

    def bit_depth_text(self):
        bits = int(
            self.track.get(
                "bitdepth",
                0,
            )
            or 0
        )

        return (
            f"{bits}-bit"
            if bits > 0
            else "Unknown"
        )

    def sample_rate_text(self):
        sample_rate = int(
            self.track.get(
                "samplerate",
                0,
            )
            or 0
        )

        if sample_rate <= 0:
            return "Unknown"

        khz = (
            sample_rate
            / 1000.0
        )

        if khz.is_integer():
            khz_text = (
                f"{int(khz)} kHz"
            )
        else:
            khz_text = (
                f"{khz:g} kHz"
            )

        return (
            f"{khz_text}"
            f" ({sample_rate:,} Hz)"
        )

    def bitrate_text(self):
        bitrate = int(
            self.metadata.get(
                "bps"
            )
            or 0
        )

        if bitrate <= 0:
            return "Unknown"

        return (
            f"{round(bitrate / 1000)} kbps"
        )

    def copy_text(self):
        path = Path(
            self.result["path"]
        )

        r128_unit = self.result.get(
            "r128_unit",
            "LUFS",
        )

        if r128_unit == "LU":
            loudness = (
                float(
                    self.result["lufs"]
                )
                + 23.0
            )
            loudness_text = (
                f"{loudness:.2f} LU"
            )
        else:
            loudness_text = (
                f"{float(self.result['lufs']):.2f} LUFS"
            )

        return (
            f"{APP_NAME} - File Information\n"
            f"\n"
            f"File\n"
            f"Name: {path.name}\n"
            f"Location: {path.parent}\n"
            f"Size: {self.file_size_text()}\n"
            f"\n"
            f"Audio\n"
            f"Format: {self.format_text()}\n"
            f"Encoding: "
            f"{self.value_or_unknown(self.metadata.get('encoding'))}\n"
            f"Channels: {self.track.get('channels', 'Unknown')}\n"
            f"Channel layout: {self.channel_layout_text()}\n"
            f"Bit depth: {self.bit_depth_text()}\n"
            f"Sample rate: {self.sample_rate_text()}\n"
            f"Bitrate: {self.bitrate_text()}\n"
            f"Duration: "
            f"{format_duration(float(self.track.get('duration', 0.0)))}\n"
            f"\n"
            f"Metadata\n"
            f"Artist: "
            f"{self.value_or_unknown(self.metadata.get('artist'))}\n"
            f"Title: "
            f"{self.value_or_unknown(self.metadata.get('title'))}\n"
            f"Album: "
            f"{self.value_or_unknown(self.metadata.get('album'))}\n"
            f"Track: "
            f"{self.value_or_unknown(self.metadata.get('track'))}\n"
            f"Date: "
            f"{self.value_or_unknown(self.metadata.get('date'))}\n"
            f"\n"
            f"Analysis\n"
            f"Dynamic Range: DR {float(self.result['dr']):.1f}\n"
            f"Integrated loudness: {loudness_text}\n"
            f"Loudness Range: {float(self.result['lra']):.2f} LU\n"
            f"Peak-to-Loudness Ratio: {float(self.result['plr']):.2f} LU\n"
            f"Crest factor: {float(self.result['crest']):.2f} dB\n"
            f"True Peak: {float(self.result['true_peak']):.2f} dBTP"
        )

    def copy_details(self):
        QApplication.clipboard().setText(
            self.copy_text()
        )

        self.copied_label.setText(
            "Copied to clipboard"
        )

        QTimer.singleShot(
            1800,
            lambda:
            self.copied_label.setText(""),
        )


# ============================================================
# Dynamics Assessment
# ============================================================


class DynamicsAssessmentDialog(QDialog):
    COMPONENT_NAMES = {
        "allpass_crest_recovery": "Allpass crest recovery",
        "peak_to_loudness_ratio": "Peak-to-Loudness Ratio",
        "short_term_density": "Short-term density",
        "loud_section_crest": "Loud-section crest",
        "integrated_loudness": "Integrated loudness",
    }

    def __init__(self, report, parent=None):
        super().__init__(parent)

        self.report = report
        self.result = report.result
        self.assessment = self.result.get("dynamics_assessment") or {}
        path = Path(self.result["path"])

        self.setWindowTitle(f"Dynamics Assessment - {path.name}")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(720, 720)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        title = QLabel(path.name)
        title.setObjectName("assessmentTitle")
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        subtitle = QLabel(
            "Explainable single-file assessment of direct level-maximization "
            "signatures in the current waveform."
        )
        subtitle.setObjectName("assessmentSubtitle")
        subtitle.setWordWrap(True)

        outer.addWidget(title)
        outer.addWidget(subtitle)

        score = float(self.assessment.get("score", 0.0) or 0.0)
        label = str(self.assessment.get("label", "Unknown"))
        confidence = str(self.assessment.get("confidence", "Unknown"))
        summary = str(self.assessment.get("summary", ""))
        index_name = str(
            self.assessment.get(
                "index_name",
                "Level Maximization Evidence",
            )
        )

        score_card = QFrame()
        score_card.setObjectName("assessmentScoreCard")
        score_layout = QGridLayout(score_card)
        score_layout.setContentsMargins(14, 12, 14, 12)
        score_layout.setHorizontalSpacing(16)
        score_layout.setVerticalSpacing(5)

        index_label = QLabel(index_name)
        index_label.setObjectName("assessmentIndexName")

        score_value = QLabel(f"{score:.1f} / 100")
        score_value.setObjectName("assessmentScoreValue")
        score_value.setStyleSheet(
            "QLabel {"
            f"background-color: {assessment_color(label)};"
            "color: white;"
            "border-radius: 7px;"
            "padding: 7px 12px;"
            "}"
        )

        label_value = QLabel(label)
        label_value.setStyleSheet("font-size: 15px; font-weight: 700;")

        confidence_value = QLabel(
            f"Measurement confidence: {confidence}"
        )
        confidence_value.setObjectName("assessmentConfidence")

        summary_label = QLabel(summary)
        summary_label.setObjectName("assessmentSummary")
        summary_label.setWordWrap(True)
        summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        score_layout.addWidget(index_label, 0, 0, 1, 2)
        score_layout.addWidget(score_value, 1, 0, 2, 1)
        score_layout.addWidget(label_value, 1, 1)
        score_layout.addWidget(confidence_value, 2, 1)
        score_layout.addWidget(summary_label, 3, 0, 1, 2)
        score_layout.setColumnStretch(1, 1)

        outer.addWidget(score_card)

        details = QTextBrowser()
        details.setObjectName("assessmentDetails")
        details.setReadOnly(True)
        details.setOpenExternalLinks(False)
        details.setHtml(self.details_html())
        outer.addWidget(details, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        copied_label = QLabel("")
        copied_label.setObjectName("assessmentCopied")
        self.copied_label = copied_label

        copy_button = QPushButton("Copy Assessment")
        copy_button.setToolTip(
            "Copy the score, supporting measurements, evidence and cautions\n"
            "to the Windows clipboard."
        )
        copy_button.clicked.connect(self.copy_assessment)

        help_button = QToolButton()
        help_button.setObjectName("headerIconButton")
        help_button.setFixedSize(34, 30)
        help_button.setIconSize(QSize(20, 20))
        help_button.setIcon(load_fluent_icon("help", getattr(parent, "system_dark", True), 20))
        help_button.setToolTip("Help")
        help_button.clicked.connect(self.open_help)

        close_button = QPushButton("Close")
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)

        footer.addWidget(copy_button)
        footer.addWidget(copied_label)
        footer.addStretch(1)
        footer.addWidget(help_button)
        footer.addWidget(close_button)
        outer.addLayout(footer)

    @staticmethod
    def metric_text(value, suffix="", digits=2):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "Unavailable"
        if not np.isfinite(value):
            return "Unavailable"
        return f"{value:.{digits}f}{suffix}"

    @staticmethod
    def html_list(items, empty_text):
        if not items:
            return f"<p>{empty_text}</p>"
        return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"

    def details_html(self):
        metrics = self.assessment.get("metrics", {})
        components = self.assessment.get("components", [])
        evidence = self.assessment.get("evidence", [])
        counter = self.assessment.get("counter_evidence", [])
        cautions = self.assessment.get("cautions", [])

        component_rows = []
        for component in components:
            name = self.COMPONENT_NAMES.get(
                component.get("name"),
                str(component.get("name", "Metric")),
            )
            points = float(component.get("points", 0.0) or 0.0)
            max_points = float(component.get("max_points", 0.0) or 0.0)
            strength = str(component.get("interpretation", ""))
            component_rows.append(
                "<tr>"
                f"<td><b>{name}</b></td>"
                f"<td>{points:.1f} / {max_points:.0f}</td>"
                f"<td>{strength}</td>"
                "</tr>"
            )

        metric_rows = [
            ("Integrated loudness", self.metric_text(metrics.get("integrated_lufs"), " LUFS")),
            ("PLR", self.metric_text(metrics.get("plr_lu"), " LU")),
            ("Loudness Range", self.metric_text(metrics.get("lra_lu"), " LU")),
            ("Dynamic Range", self.metric_text(metrics.get("dr"), "", 1)),
            ("Crest factor", self.metric_text(metrics.get("crest_total_db"), " dB")),
            ("True Peak", self.metric_text(metrics.get("true_peak_dbtp"), " dBTP")),
            ("Allpass recovery (median)", self.metric_text(metrics.get("allpass_recovery_median_db"), " dB")),
            ("Short-term PLR (median)", self.metric_text(metrics.get("short_term_plr_median_lu"), " LU")),
            ("Loud-section crest", self.metric_text(metrics.get("loud_section_crest_median_db"), " dB")),
        ]
        metric_html = "".join(
            f"<tr><td><b>{name}</b></td><td>{value}</td></tr>"
            for name, value in metric_rows
        )

        return (
            "<h3>Why this score?</h3>"
            "<h4>Evidence</h4>"
            + self.html_list(evidence, "No strong positive evidence item was identified.")
            + "<h4>Counter-evidence / ambiguity</h4>"
            + self.html_list(counter, "No strong counter-evidence item was identified.")
            + "<h3>Score contribution</h3>"
            + "<table cellspacing='3' cellpadding='4' width='100%'>"
            + "<tr><th align='left'>Indicator</th><th align='left'>Points</th><th align='left'>Strength</th></tr>"
            + "".join(component_rows)
            + "</table>"
            + "<p><i>DR and LRA are context measurements and do not directly add score points.</i></p>"
            + "<h3>Key measurements</h3>"
            + "<table cellspacing='3' cellpadding='4' width='100%'>"
            + metric_html
            + "</table>"
            + "<h3>Important notes</h3>"
            + self.html_list(cautions, "No additional cautions.")
        )

    def copy_text(self):
        a = self.assessment
        metrics = a.get("metrics", {})
        components = a.get("components", [])
        path = Path(self.result["path"])

        lines = [
            f"{APP_NAME} - Dynamics Assessment",
            "",
            f"File: {path.name}",
            f"Level Maximization Evidence: {float(a.get('score', 0.0)):.1f} / 100 - {a.get('label', 'Unknown')}",
            f"Measurement confidence: {a.get('confidence', 'Unknown')}",
            f"Summary: {a.get('summary', '')}",
            "",
            "Score contribution:",
        ]

        for component in components:
            name = self.COMPONENT_NAMES.get(
                component.get("name"),
                str(component.get("name", "Metric")),
            )
            lines.append(
                f"- {name}: {float(component.get('points', 0.0)):.1f} / "
                f"{float(component.get('max_points', 0.0)):.0f} "
                f"({component.get('interpretation', '')})"
            )

        lines.extend([
            "",
            "Key measurements:",
            f"- Integrated loudness: {self.metric_text(metrics.get('integrated_lufs'), ' LUFS')}",
            f"- PLR: {self.metric_text(metrics.get('plr_lu'), ' LU')}",
            f"- LRA: {self.metric_text(metrics.get('lra_lu'), ' LU')}",
            f"- DR: {self.metric_text(metrics.get('dr'), '', 1)}",
            f"- Crest factor: {self.metric_text(metrics.get('crest_total_db'), ' dB')}",
            f"- True Peak: {self.metric_text(metrics.get('true_peak_dbtp'), ' dBTP')}",
            f"- Allpass recovery (median): {self.metric_text(metrics.get('allpass_recovery_median_db'), ' dB')}",
            f"- Short-term PLR (median): {self.metric_text(metrics.get('short_term_plr_median_lu'), ' LU')}",
            f"- Loud-section crest: {self.metric_text(metrics.get('loud_section_crest_median_db'), ' dB')}",
            "",
            "Evidence:",
        ])
        lines.extend(f"- {item}" for item in a.get("evidence", []))
        lines.extend(["", "Counter-evidence / ambiguity:"])
        lines.extend(f"- {item}" for item in a.get("counter_evidence", []))
        lines.extend(["", "Important notes:"])
        lines.extend(f"- {item}" for item in a.get("cautions", []))
        return "\n".join(lines)

    def copy_assessment(self):
        QApplication.clipboard().setText(self.copy_text())
        self.copied_label.setText("Copied to clipboard")
        QTimer.singleShot(1800, lambda: self.copied_label.setText(""))

    def open_help(self):
        HelpDialog(self, initial_page="Dynamics Assessment").exec()


# ============================================================
# Dynamics Comparison
# ============================================================


class DynamicsComparisonDialog(QDialog):
    def __init__(self, result, dark=True, parent=None):
        super().__init__(parent)

        self.result = result
        self.interpretation = result.get("dynamics_comparison") or {}
        self.version_a = result.get("version_a") or {}
        self.version_b = result.get("version_b") or {}
        self.dark = bool(dark)

        self.setWindowTitle("Dynamics Comparison")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(860, 760)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(10)

        title = QLabel("Dynamics Comparison")
        title.setObjectName("assessmentTitle")
        subtitle = QLabel(
            "Measured DR beside independently aligned Short-Term loudness dynamics."
        )
        subtitle.setObjectName("assessmentSubtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(subtitle)

        versions = QHBoxLayout()
        versions.setSpacing(10)
        versions.addWidget(self.version_card("A", self.version_a), 1)
        versions.addWidget(self.version_card("B", self.version_b), 1)
        outer.addLayout(versions)

        # Give the aligned loudness-dynamics verdict the same kind of immediate
        # visual weight as the DR meter above it.  LDS is similarity, not a
        # quality score, so the badge uses a value-neutral blue progression
        # rather than a red/orange/green good/bad-style scale.
        similarity = self.interpretation.get("dynamics_similarity") or {}
        similarity_score = similarity.get("score")
        similarity_label = str(similarity.get("label", "Inconclusive"))

        musical_card = QFrame()
        musical_card.setObjectName("assessmentScoreCard")
        musical_layout = QGridLayout(musical_card)
        musical_layout.setContentsMargins(14, 10, 14, 10)
        musical_layout.setHorizontalSpacing(16)
        musical_layout.setVerticalSpacing(4)

        musical_title = QLabel("Loudness Dynamics Similarity")
        musical_title.setStyleSheet("font-weight: 700;")

        if similarity_score is None:
            similarity_badge_text = "Inconclusive"
        else:
            similarity_badge_text = f"{float(similarity_score):.1f} / 100"

        similarity_badge = QLabel(similarity_badge_text)
        similarity_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        similarity_badge.setStyleSheet(
            "QLabel {"
            f"background-color: {comparison_similarity_color(similarity_label)};"
            "color: white;"
            "font-size: 15px; font-weight: 700;"
            "border-radius: 7px; padding: 6px 11px;"
            "}"
        )

        similarity_text = QLabel(
            similarity_label if similarity_score is None
            else f"{similarity_label} similarity"
        )
        similarity_text.setStyleSheet("font-size: 14px; font-weight: 700;")

        advantage_text = QLabel(
            f"Loudness Dynamics Advantage: {self.loudness_advantage_text()}"
        )
        advantage_text.setObjectName("assessmentConfidence")
        advantage_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        musical_layout.addWidget(musical_title, 0, 0, 1, 2)
        musical_layout.addWidget(similarity_badge, 1, 0, 2, 1)
        musical_layout.addWidget(similarity_text, 1, 1)
        musical_layout.addWidget(advantage_text, 2, 1)
        musical_layout.setColumnStretch(1, 1)
        outer.addWidget(musical_card)

        conclusion = self.interpretation.get("conclusion") or {}
        conclusion_card = QFrame()
        conclusion_card.setObjectName("assessmentScoreCard")
        conclusion_layout = QVBoxLayout(conclusion_card)
        conclusion_layout.setContentsMargins(14, 10, 14, 10)
        conclusion_layout.setSpacing(4)

        conclusion_title = QLabel(str(conclusion.get("title", "Comparison")))
        conclusion_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        conclusion_summary = QLabel(str(conclusion.get("summary", "")))
        conclusion_summary.setWordWrap(True)
        conclusion_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        conclusion_layout.addWidget(conclusion_title)
        conclusion_layout.addWidget(conclusion_summary)
        outer.addWidget(conclusion_card)

        summary_card = QFrame()
        summary_card.setObjectName("assessmentScoreCard")
        grid = QGridLayout(summary_card)
        grid.setContentsMargins(14, 10, 14, 10)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(7)

        rows = [
            ("Loudness Dynamics Similarity", self.dynamics_similarity_text()),
            ("Loudness Curve Similarity", self.curve_similarity_text()),
            ("Loudness Dynamics Advantage", self.loudness_advantage_text()),
            ("Level Difference", self.level_difference_text()),
            ("Peak Structure Difference", self.peak_structure_text()),
            ("Alignment", str(result.get("alignment_status", "Unknown"))),
        ]
        for row, (name, value) in enumerate(rows):
            key = QLabel(name)
            key.setStyleSheet("font-weight: 700;")
            val = QLabel(value)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(key, row, 0)
            grid.addWidget(val, row, 1)
        grid.setColumnStretch(1, 1)
        outer.addWidget(summary_card)

        details = QTextBrowser()
        details.setObjectName("assessmentDetails")
        details.setReadOnly(True)
        details.setOpenExternalLinks(False)
        details.setHtml(self.details_html())
        outer.addWidget(details, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        copy_button = QPushButton("Copy Comparison")
        copy_button.setToolTip("Copy the comparison result and supporting measurements to the clipboard.")
        copy_button.clicked.connect(self.copy_comparison)

        self.copied_label = QLabel("")
        self.copied_label.setObjectName("assessmentCopied")

        help_button = QToolButton()
        help_button.setObjectName("headerIconButton")
        help_button.setFixedSize(34, 30)
        help_button.setIconSize(QSize(20, 20))
        help_button.setIcon(load_fluent_icon("help", self.dark, 20))
        help_button.setToolTip("Help")
        help_button.clicked.connect(self.open_help)

        close_button = QPushButton("Close")
        close_button.setDefault(True)
        close_button.clicked.connect(self.accept)

        footer.addWidget(copy_button)
        footer.addWidget(self.copied_label)
        footer.addStretch(1)
        footer.addWidget(help_button)
        footer.addWidget(close_button)
        outer.addLayout(footer)

    @staticmethod
    def fmt(value, suffix="", digits=2):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "Unavailable"
        if not np.isfinite(value):
            return "Unavailable"
        return f"{value:.{digits}f}{suffix}"

    def version_card(self, side, version):
        frame = QFrame()
        frame.setObjectName("assessmentScoreCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(5)

        filename = str(version.get("filename") or Path(str(version.get("path", ""))).name or f"Version {side}")
        name = QLabel(f"Version {side} — {filename}")
        name.setStyleSheet("font-weight: 700;")
        name.setWordWrap(True)
        name.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        # Reserve exactly two title lines in both cards so a wrapped filename
        # can never push one DR meter lower than the other.  The full name
        # remains available through the tooltip if it exceeds that area.
        name.setFixedHeight(name.fontMetrics().lineSpacing() * 2 + 4)
        name.setToolTip(filename)
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        measured = self.interpretation.get("measured_dr") or {}
        dr = measured.get("version_a" if side == "A" else "version_b")
        try:
            dr_num = float(dr)
        except (TypeError, ValueError):
            dr_num = -1.0
        dr_label = QLabel("DR ??.?" if dr_num < 0 else f"DR {dr_num:.1f}")
        text_color = "#111111" if dr_num >= 10 else "#ffffff"
        dr_label.setStyleSheet(
            "QLabel {"
            f"background-color: {dr_color(dr_num)};"
            f"color: {text_color};"
            "font-family: Consolas, 'Courier New', monospace;"
            "font-size: 18px; font-weight: 700;"
            "border-radius: 7px; padding: 6px 10px;"
            "}"
        )
        dr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        winner = str(measured.get("higher_measured_dr", "Unavailable"))
        delta = measured.get("delta_b_minus_a")
        note = "Measured DR"
        if winner == side:
            try:
                diff = abs(float(delta))
                note = f"Higher measured DR (+{diff:.1f})"
            except (TypeError, ValueError):
                note = "Higher measured DR"
        elif winner == "Equal":
            note = "Measured DR — essentially equal"
        note_label = QLabel(note)
        note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if winner == side:
            note_label.setStyleSheet("font-weight: 700;")

        layout.addWidget(name)
        layout.addWidget(dr_label)
        layout.addWidget(note_label)
        return frame

    def dynamics_similarity_text(self):
        data = self.interpretation.get("dynamics_similarity") or {}
        score = data.get("score")
        if score is None:
            return str(data.get("label", "Inconclusive"))
        return f"{float(score):.1f} / 100 — {data.get('label', '')}"

    def curve_similarity_text(self):
        data = self.interpretation.get("dynamics_similarity") or {}
        value = data.get("loudness_curve_similarity_percent")
        if value is None:
            return "Unavailable"
        return f"{float(value):.2f}%"

    def loudness_advantage_text(self):
        data = self.interpretation.get("musical_dynamics_advantage") or {}
        direction = str(data.get("direction", "Inconclusive"))
        strength = str(data.get("strength", ""))
        if direction == "None":
            return "None detected"
        if direction in ("A", "B"):
            return f"{strength} — Version {direction}"
        return strength or direction

    def level_difference_text(self):
        value = self.interpretation.get("level_difference_b_minus_a_db")
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "Unavailable"
        if not np.isfinite(value):
            return "Unavailable"
        if abs(value) < 0.10:
            return "Essentially equal"
        if value > 0:
            return f"Version B is {abs(value):.2f} dB louder"
        return f"Version B is {abs(value):.2f} dB quieter"

    def peak_structure_text(self):
        data = self.interpretation.get("peak_structure_difference") or {}
        score = data.get("score")
        if score is None:
            return str(data.get("label", "Unavailable"))
        return f"{float(score):.1f} / 100 — {data.get('label', '')}"

    def details_html(self):
        ia = self.version_a.get("metrics") or {}
        ib = self.version_b.get("metrics") or {}
        loudness_dynamics = self.interpretation.get("musical_dynamics_advantage") or {}
        peaks = self.interpretation.get("peak_structure_difference") or {}
        headroom = self.interpretation.get("peak_headroom") or {}
        short = self.result.get("short_term_loudness") or {}
        alignment = self.result.get("alignment") or {}
        notes = list(self.result.get("alignment_notes") or [])
        cautions = list(self.interpretation.get("cautions") or [])

        def e(text):
            return html.escape(str(text))

        def metric_row(name, a, b, suffix="", digits=2):
            return (
                f"<tr><td><b>{e(name)}</b></td>"
                f"<td>{e(self.fmt(a, suffix, digits))}</td>"
                f"<td>{e(self.fmt(b, suffix, digits))}</td></tr>"
            )

        rows = "".join([
            metric_row("Measured DR", ia.get("dr"), ib.get("dr"), "", 1),
            metric_row("Integrated loudness", ia.get("integrated_lufs"), ib.get("integrated_lufs"), " LUFS"),
            metric_row("PLR", ia.get("plr_lu"), ib.get("plr_lu"), " LU"),
            metric_row("LRA", ia.get("lra_lu"), ib.get("lra_lu"), " LU"),
            metric_row("Crest factor", ia.get("crest_total_db"), ib.get("crest_total_db"), " dB"),
            metric_row("True Peak", ia.get("true_peak_dbtp"), ib.get("true_peak_dbtp"), " dBTP"),
            metric_row("Allpass recovery (median)", ia.get("allpass_recovery_median_db"), ib.get("allpass_recovery_median_db"), " dB"),
        ])

        similarity = self.interpretation.get("dynamics_similarity") or {}
        sim_components = similarity.get("components") or {}
        peak_raw = self.result.get("peak_crest") or {}

        reasoning = list(loudness_dynamics.get("reasoning") or [])
        if not reasoning:
            reasoning = ["No additional loudness-dynamics reasoning is available."]

        return (
            "<h3>Why this conclusion?</h3>"
            + "<ul>" + "".join(f"<li>{e(item)}</li>" for item in reasoning) + "</ul>"
            + "<h3>Version measurements</h3>"
            + "<table cellspacing='3' cellpadding='4' width='100%'>"
            + "<tr><th align='left'>Metric</th><th align='left'>Version A</th><th align='left'>Version B</th></tr>"
            + rows + "</table>"
            + "<h3>Loudness Dynamics Similarity contribution</h3>"
            + "<table cellspacing='3' cellpadding='4' width='100%'>"
            + f"<tr><td><b>Trajectory correlation</b></td><td>{e(self.fmt(sim_components.get('trajectory_correlation_points'), ' / 100', 1))}</td><td>55%</td></tr>"
            + f"<tr><td><b>Residual similarity</b></td><td>{e(self.fmt(sim_components.get('residual_similarity_points'), ' / 100', 1))}</td><td>30%</td></tr>"
            + f"<tr><td><b>Loudness-span similarity</b></td><td>{e(self.fmt(sim_components.get('loudness_span_similarity_points'), ' / 100', 1))}</td><td>15%</td></tr>"
            + "</table>"
            + "<h3>Aligned comparison details</h3>"
            + "<table cellspacing='3' cellpadding='4' width='100%'>"
            + f"<tr><td><b>Short-Term span delta (B-A)</b></td><td>{e(self.fmt(short.get('span_delta_b_minus_a_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Combined loudness-dynamics delta (B-A)</b></td><td>{e(self.fmt(loudness_dynamics.get('combined_delta_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Residual p90 after level match</b></td><td>{e(self.fmt(short.get('residual_p90_abs_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>PLR delta (B-A)</b></td><td>{e(self.fmt(headroom.get('plr_delta_b_minus_a_lu'), ' LU'))}</td></tr>"
            + f"<tr><td><b>Higher PLR</b></td><td>{e(headroom.get('higher_plr', 'Unavailable'))}</td></tr>"
            + f"<tr><td><b>Peak structure direction</b></td><td>{e(peaks.get('direction', 'Unavailable'))}</td></tr>"
            + f"<tr><td><b>Peak lift after level match (median)</b></td><td>{e(self.fmt(peak_raw.get('peak_lift_after_level_match_median_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Peak lift after level match (p90)</b></td><td>{e(self.fmt(peak_raw.get('peak_lift_after_level_match_p90_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Crest delta (median)</b></td><td>{e(self.fmt(peak_raw.get('crest_delta_median_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Crest delta (p90)</b></td><td>{e(self.fmt(peak_raw.get('crest_delta_p90_db'), ' dB'))}</td></tr>"
            + f"<tr><td><b>Alignment offset</b></td><td>{e(self.fmt(alignment.get('offset_seconds'), ' s'))}</td></tr>"
            + f"<tr><td><b>Speed difference</b></td><td>{e(self.fmt(alignment.get('speed_difference_percent'), '%'))}</td></tr>"
            + "</table>"
            + ("<h3>Alignment notes</h3><ul>" + "".join(f"<li>{e(item)}</li>" for item in notes) + "</ul>" if notes else "")
            + "<h3>Important notes</h3><ul>"
            + "".join(f"<li>{e(item)}</li>" for item in cautions)
            + "</ul>"
        )

    def copy_text(self):
        measured = self.interpretation.get("measured_dr") or {}
        loudness_dynamics = self.interpretation.get("musical_dynamics_advantage") or {}
        peaks = self.interpretation.get("peak_structure_difference") or {}
        conclusion = self.interpretation.get("conclusion") or {}
        lines = [
            f"{APP_NAME} - Dynamics Comparison",
            "",
            f"Version A: {self.version_a.get('filename', '')}",
            f"Version B: {self.version_b.get('filename', '')}",
            f"Measured DR: A DR {measured.get('version_a', 'Unavailable')} | B DR {measured.get('version_b', 'Unavailable')}",
            f"Higher measured DR: {measured.get('higher_measured_dr', 'Unavailable')}",
            f"Loudness Dynamics Similarity: {self.dynamics_similarity_text()}",
            f"Loudness Curve Similarity: {self.curve_similarity_text()}",
            f"Loudness Dynamics Advantage: {self.loudness_advantage_text()}",
            f"Level Difference: {self.level_difference_text()}",
            f"Peak Structure Difference: {self.peak_structure_text()}",
            f"Alignment: {self.result.get('alignment_status', 'Unknown')}",
            "",
            f"Conclusion: {conclusion.get('title', '')}",
            str(conclusion.get("summary", "")),
            "",
            "Loudness-dynamics reasoning:",
        ]
        lines.extend(f"- {item}" for item in loudness_dynamics.get("reasoning", []))
        lines.extend([
            "",
            "Notes:",
        ])
        lines.extend(f"- {item}" for item in self.interpretation.get("cautions", []))
        return "\n".join(lines)

    def copy_comparison(self):
        QApplication.clipboard().setText(self.copy_text())
        self.copied_label.setText("Copied to clipboard")
        QTimer.singleShot(1800, lambda: self.copied_label.setText(""))

    def open_help(self):
        HelpDialog(self, initial_page="Dynamics Comparison").exec()


class DynamicsComparisonWorker(QObject):
    status = Signal(str)
    finished = Signal(object)
    failed = Signal(str, str)

    def __init__(self, entry_a, entry_b):
        super().__init__()
        self.entry_a = dict(entry_a)
        self.entry_b = dict(entry_b)

    def run(self):
        try:
            result = compare_files(
                Path(self.entry_a["path"]),
                Path(self.entry_b["path"]),
                metrics_a=dict(self.entry_a.get("dynamics_metrics") or {}),
                metrics_b=dict(self.entry_b.get("dynamics_metrics") or {}),
                progress_callback=self.status.emit,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc), traceback.format_exc())


class DynamicsComparisonProgressDialog(QDialog):
    def __init__(self, entry_a, entry_b, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dynamics Comparison")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedSize(460, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(9)

        files = QLabel(
            f"{entry_a.get('title', 'Version A')}  ↔  {entry_b.get('title', 'Version B')}"
        )
        files.setObjectName("processingFilename")
        files.setAlignment(Qt.AlignmentFlag.AlignCenter)
        files.setWordWrap(True)

        self.status_label = QLabel("Preparing comparison...")
        self.status_label.setObjectName("processingStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        progress = QProgressBar()
        progress.setRange(0, 0)

        layout.addWidget(files)
        layout.addWidget(self.status_label)
        layout.addWidget(progress)

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is None:
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(parent.frameGeometry().center())
        self.move(geometry.topLeft())


# ============================================================
# Advanced Open dialog
# ============================================================


class AdvancedOpenDialog(QDialog):
    """Windows-native Advanced Open surface with MasVisGtk semantics."""

    def __init__(self, dark, initial_directory=None, parent=None):
        super().__init__(parent)

        self.dark = dark
        self.path_items = {}
        self.last_directory = _existing_directory(initial_directory)

        self.setWindowTitle("Advanced Open")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(640, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Compact in-dialog command bar. Qt can technically replace the
        # native title bar, but keeping Windows chrome and placing the
        # command bar directly below it is more consistent and robust.
        toolbar = QFrame()
        toolbar.setObjectName("advancedToolbar")
        toolbar.setFixedHeight(50)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 6, 10, 6)
        toolbar_layout.setSpacing(4)

        self.add_files_button = self.create_icon_button(
            "add_files",
            "Add Files",
        )
        self.add_files_button.clicked.connect(self.add_files)

        self.add_folder_button = self.create_icon_button(
            "add_folder",
            "Add Folder",
        )
        self.add_folder_button.clicked.connect(self.add_folder)

        toolbar_layout.addWidget(self.add_files_button)
        toolbar_layout.addWidget(self.add_folder_button)
        toolbar_layout.addStretch(1)

        outer.addWidget(toolbar)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 14, 16, 14)
        body_layout.setSpacing(12)

        # Options -----------------------------------------------------
        options_title = QLabel("Options")
        options_title.setObjectName("advancedSectionTitle")
        body_layout.addWidget(options_title)

        options_frame = QFrame()
        options_frame.setObjectName("advancedOptions")

        options_layout = QVBoxLayout(options_frame)
        options_layout.setContentsMargins(12, 10, 12, 10)
        options_layout.setSpacing(9)

        row_one = QHBoxLayout()
        row_one.setSpacing(8)

        loudness_label = QLabel("Loudness units:")

        self.loudness_combo = QComboBox()
        self.loudness_combo.addItem("LUFS", "LUFS")
        self.loudness_combo.addItem("LU", "LU")
        self.loudness_combo.setFixedWidth(100)

        self.recursive_check = QCheckBox("Search subfolders")
        self.recursive_check.setChecked(True)
        self.recursive_check.setToolTip(
            "When a folder is added, include supported audio files "
            "from its subfolders as well."
        )

        row_one.addWidget(loudness_label)
        row_one.addWidget(self.loudness_combo)
        row_one.addSpacing(18)
        row_one.addWidget(self.recursive_check)
        row_one.addStretch(1)

        row_two = QHBoxLayout()
        row_two.setSpacing(8)

        overview_label = QLabel("Overview mode:")

        self.overview_combo = QComboBox()
        self.overview_combo.addItem(
            "Off (detailed tabs)",
            None,
        )
        self.overview_combo.addItem(
            "All files (flat)",
            "flat",
        )
        self.overview_combo.addItem(
            "By folder (dir)",
            "dir",
        )
        self.overview_combo.setMinimumWidth(210)
        self.overview_combo.setToolTip(
            "Off creates a detailed tab for each file. "
            "Flat creates one overview for all files. "
            "Dir creates one overview per containing folder."
        )

        row_two.addWidget(overview_label)
        row_two.addWidget(self.overview_combo)
        row_two.addStretch(1)

        options_layout.addLayout(row_one)
        options_layout.addLayout(row_two)

        body_layout.addWidget(options_frame)

        # Input list --------------------------------------------------
        list_header = QHBoxLayout()

        list_title = QLabel("Files and folders")
        list_title.setObjectName("advancedSectionTitle")

        self.count_label = QLabel("0 items")
        self.count_label.setObjectName("advancedCount")

        list_header.addWidget(list_title)
        list_header.addStretch(1)
        list_header.addWidget(self.count_label)

        body_layout.addLayout(list_header)

        self.path_list = QListWidget()
        self.path_list.setObjectName("advancedList")
        self.path_list.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.path_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        body_layout.addWidget(self.path_list, 1)

        # Buttons -----------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self.start_button = QPushButton("Start")
        self.start_button.setFixedWidth(92)
        self.start_button.setDefault(True)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.accept)

        cancel_button = QPushButton("Cancel")
        cancel_button.setFixedWidth(92)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(self.start_button)
        buttons.addWidget(cancel_button)

        body_layout.addLayout(buttons)
        outer.addWidget(body, 1)

    def create_icon_button(self, icon_kind, tooltip):
        button = QToolButton()
        button.setObjectName("headerIconButton")
        button.setFixedSize(HEADER_BUTTON_SIZE, HEADER_BUTTON_SIZE)
        button.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        button.setIcon(
            load_fluent_icon(
                icon_kind,
                self.dark,
                TOOLBAR_ICON_SIZE,
            )
        )
        button.setToolTip(tooltip)
        return button

    @staticmethod
    def path_key(path):
        # Case-insensitive keys match normal Windows path semantics.
        return str(Path(path).absolute()).casefold()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Files",
            str(self.last_directory),
            AUDIO_FILTER,
        )

        if paths:
            self.last_directory = Path(paths[0]).parent

        for path in paths:
            self.add_path(Path(path))

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Add Folder",
            str(self.last_directory),
        )

        if path:
            self.last_directory = Path(path)
            self.add_path(Path(path))

    def add_path(self, path):
        path = Path(path).absolute()
        key = self.path_key(path)

        if key in self.path_items:
            return

        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 38))

        row = QWidget()
        row.setObjectName("advancedPathRow")

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 2, 4, 2)
        row_layout.setSpacing(6)

        label = QLabel(str(path))
        label.setObjectName("advancedPathLabel")
        label.setToolTip(str(path))
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        remove_button = QToolButton()
        remove_button.setObjectName("removePathButton")
        remove_button.setFixedSize(30, 30)
        remove_button.setIconSize(QSize(20, 20))
        remove_button.setIcon(
            load_fluent_icon(
                "dismiss",
                self.dark,
                20,
            )
        )
        remove_button.setToolTip("Remove")
        remove_button.clicked.connect(
            lambda checked=False, list_item=item, item_key=key:
            self.remove_path(list_item, item_key)
        )

        row_layout.addWidget(label, 1)
        row_layout.addWidget(remove_button)

        self.path_list.addItem(item)
        self.path_list.setItemWidget(item, row)

        self.path_items[key] = (item, path)
        self.update_count()

    def remove_path(self, item, key):
        row = self.path_list.row(item)

        if row >= 0:
            self.path_list.takeItem(row)

        self.path_items.pop(key, None)
        self.update_count()

    def update_count(self):
        count = len(self.path_items)
        suffix = "item" if count == 1 else "items"
        self.count_label.setText(f"{count} {suffix}")
        self.start_button.setEnabled(count > 0)

    def configuration(self):
        paths = [
            path
            for item, path in self.path_items.values()
        ]

        return {
            "inputs": paths,
            "r128_unit": self.loudness_combo.currentData(),
            "recursive": self.recursive_check.isChecked(),
            "overview_mode": self.overview_combo.currentData(),
            "last_directory": str(self.last_directory),
        }


# ============================================================
# Worker
# ============================================================


class AnalysisCancelled(Exception):
    """Internal cooperative-cancellation marker for the analysis worker."""


class AnalysisWorker(QObject):
    progress = Signal(int)
    status = Signal(str)
    file_started = Signal(int, int, str)
    item_finished = Signal(object)
    overview_finished = Signal(object)
    item_failed = Signal(str, str, str)
    batch_finished = Signal(bool)

    def __init__(
        self,
        file_paths,
        r128_unit="LUFS",
        overview_mode=None,
        render_scale=RENDER_SCALE,
        report_font="",
        report_theme="Light",
    ):
        super().__init__()

        self.file_paths = [Path(path) for path in file_paths]
        self.r128_unit = r128_unit
        self.overview_mode = overview_mode
        self.render_scale = max(1, int(render_scale))
        self.report_font = report_font or ""
        self.report_theme = report_theme or "Light"
        self.cancel_event = threading.Event()
        self.current_index = 0
        self.current_total = len(self.file_paths)
        self.overview_groups = {}

    def request_cancel(self):
        # threading.Event.set() is intentionally the only operation here.  It
        # is safe to call directly from the GUI thread even though this QObject
        # lives in the worker thread.  A queued Qt call would not run while
        # run() is busy doing the analysis itself.
        self.cancel_event.set()

    def raise_if_cancelled(self):
        if self.cancel_event.is_set():
            raise AnalysisCancelled()

    def masvis_callback(self, event, tid, desc=None, secs=None):
        if event != "start":
            return

        # MasVis calls this callback at the start of every major analysis and
        # render step.  Cancellation is raised only between analysis steps.
        # Once Matplotlib rendering has started, let that render complete so
        # upstream figure cleanup can run normally; run() checks the flag again
        # immediately afterward.
        if tid is None or tid < Steps.draw_plot:
            self.raise_if_cancelled()

        if desc:
            self.status.emit(desc)

        if tid is None:
            return

        local_fraction = max(
            0.0,
            min(float(tid) / float(Steps.steps - 1), 1.0),
        )

        overall_fraction = (
            self.current_index + local_fraction
        ) / max(self.current_total, 1)

        value = int(round(overall_fraction * 100))
        self.progress.emit(max(0, min(value, 99)))

    def run(self):
        cancelled = False

        for index, path in enumerate(self.file_paths):
            if self.cancel_event.is_set():
                cancelled = True
                break

            self.current_index = index

            self.file_started.emit(
                index + 1,
                self.current_total,
                path.name,
            )

            try:
                self.status.emit("Decoding audio...")
                track = load_audio(path, cancel_event=self.cancel_event)

                track["metadata"]["bps"] = int(
                    track["metadata"]["bps"] or 0
                )

                self.raise_if_cancelled()

                self.status.emit("Analyzing audio...")

                analysis = analyze(
                    track,
                    callback=self.masvis_callback,
                )
                self.raise_if_cancelled()

                for key in (
                    "crest_total_db",
                    "l_kg",
                    "lra",
                    "plr_lu",
                ):
                    analysis[key] = scalar(analysis[key])

                self.status.emit("Assessing dynamics...")
                dynamics_assessment = assess_dynamics(
                    track,
                    analysis,
                ).to_dict()
                self.raise_if_cancelled()

                self.status.emit("Rendering report...")

                if self.overview_mode is None:
                    # Detailed reports keep the high-resolution Windows
                    # supersampling path introduced in Prototype 0.3.
                    detailed, _overview = render_high_resolution(
                        track=track,
                        analysis=analysis,
                        header=path.stem,
                        r128_unit=self.r128_unit,
                        render_overview=False,
                        callback=self.masvis_callback,
                        render_scale=self.render_scale,
                        report_font=self.report_font,
                    )
                    detailed_png = apply_report_theme_to_png(
                        detailed.getvalue(),
                        self.report_theme,
                    )
                    overview_png = None
                else:
                    # Overview uses a dedicated Windows implementation based
                    # on modern MasVisGtk's 1212 px interactive overview.
                    self.status.emit("Rendering overview...")
                    detailed_png = b""
                    overview_png = render_modern_overview_row(
                        track,
                        analysis,
                        path.stem,
                        self.r128_unit,
                        report_font=self.report_font,
                    )

                self.raise_if_cancelled()

                result = {
                    "path": path,
                    "png_data": detailed_png,
                    "r128_unit": self.r128_unit,
                    "default_save_name": path.stem + " - MasVis.png",
                    "render_scale": self.render_scale,
                    "report_theme": self.report_theme,
                    "dr": float(analysis["dr"]),
                    "dr_channels": analysis.get("dr_channels"),
                    "channel_layout": track.get("channel_layout", ""),
                    "lufs": float(analysis["l_kg"]),
                    "lra": float(analysis["lra"]),
                    "plr": float(analysis["plr_lu"]),
                    "crest": float(analysis["crest_total_db"]),
                    "true_peak": float(max(analysis["true_peak_dbtp"])),
                    "dynamics_assessment": dynamics_assessment,
                    "track": {
                        "samplerate": track["samplerate"],
                        "bitdepth": track["bitdepth"],
                        "channels": track["channels"],
                        "duration": track["duration"],
                        "format": track.get("format", ""),
                        "metadata": dict(track["metadata"]),
                    },
                }

                if self.overview_mode is None:
                    self.item_finished.emit(result)
                elif overview_png is not None:
                    group_key = (
                        None
                        if self.overview_mode == "flat"
                        else path.parent
                    )

                    self.overview_groups.setdefault(
                        group_key,
                        [],
                    ).append(
                        {
                            "path": path,
                            "png_data": overview_png,
                        }
                    )

                file_progress = int(
                    round(((index + 1) / self.current_total) * 100)
                )
                self.progress.emit(file_progress)

            except (AnalysisCancelled, AudioLoadCancelled):
                cancelled = True
                break
            except Exception as exc:
                self.item_failed.emit(
                    str(path),
                    str(exc),
                    traceback.format_exc(),
                )

        if self.cancel_event.is_set():
            cancelled = True

        if (
            not cancelled
            and self.overview_mode is not None
            and self.overview_groups
        ):
            overview_tabs = []

            for group_key, rows in self.overview_groups.items():
                png_data = compose_overview_png(
                    [row["png_data"] for row in rows]
                )

                if png_data is None:
                    continue

                png_data = apply_report_theme_to_png(
                    png_data,
                    self.report_theme,
                )

                if group_key is None:
                    label = "Overview"
                    tooltip = "All processed files"
                    default_name = "Overview - MasVis.png"
                else:
                    label = group_key.name or str(group_key)
                    tooltip = str(group_key)
                    default_name = label + " - Overview - MasVis.png"

                overview_tabs.append(
                    {
                        "label": label,
                        "tooltip": tooltip,
                        "png_data": png_data,
                        "default_save_name": default_name,
                        "source_paths": [row["path"] for row in rows],
                        "overview_mode": self.overview_mode,
                    }
                )

            if overview_tabs:
                self.overview_finished.emit(overview_tabs)

        self.batch_finished.emit(cancelled)


# ============================================================
# Processing dialog
# ============================================================


class ProcessingDialog(QDialog):
    def __init__(self, total_files, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Processing")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(360, 205)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(9)

        self.counter_label = QLabel(f"1 / {total_files}")
        self.counter_label.setObjectName("processingCounter")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.filename_label = QLabel("")
        self.filename_label.setObjectName("processingFilename")
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Preparing...")
        self.status_label.setObjectName("processingStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedWidth(92)
        self.cancel_button.setToolTip(
            "Requests cancellation at the next safe analysis checkpoint. "
            "The current calculation step may need to finish first."
        )

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)

        layout.addWidget(self.counter_label)
        layout.addWidget(self.filename_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addLayout(button_row)

    def set_current_file(self, current, total, filename):
        self.counter_label.setText(f"{current} / {total}")
        self.filename_label.setText(filename)
        self.filename_label.setToolTip(filename)

    def request_cancel_visual(self):
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.status_label.setText("Cancelling at the next safe checkpoint...")

    def showEvent(self, event):
        super().showEvent(event)

        parent = self.parentWidget()
        if parent is None:
            return

        geometry = self.frameGeometry()
        geometry.moveCenter(parent.frameGeometry().center())
        self.move(geometry.topLeft())


# ============================================================
# DR details
# ============================================================


class DRDetailsDialog(QDialog):
    def __init__(self, report, show_chart_callback, parent=None):
        super().__init__(parent)

        self.show_chart_callback = show_chart_callback

        self.setWindowTitle("Dynamic Range")
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedWidth(330)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 20)
        layout.setSpacing(12)

        dr = float(report.result["dr"])

        dr_label = QLabel(
            f"DR {dr:.1f}" if dr >= 0 else "DR ??.?"
        )
        dr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        color = dr_color(dr)
        text_color = "#111111" if dr >= 10 else "#ffffff"

        dr_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {color};
                color: {text_color};
                border: 2px solid #e5e5e5;
                border-radius: 8px;
                padding: 6px 13px;
                font-family: Consolas, "Courier New", monospace;
                font-size: 19px;
                font-weight: 700;
            }}
            """
        )

        layout.addWidget(
            dr_label,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

        layout_name = (
            report.result.get("channel_layout")
            or "Channels"
        )

        title = QLabel(str(layout_name).title())
        title.setObjectName("channelLayoutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        channels = report.result.get("dr_channels")

        if channels is None or len(channels) == 0:
            unavailable = QLabel(
                "Channel Dynamic Range is unavailable."
            )
            unavailable.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(unavailable)
        else:
            for index, value in enumerate(channels, start=1):
                row = QHBoxLayout()

                channel_label = QLabel(f"Channel #{index}")
                value_label = QLabel()

                try:
                    value_label.setText(f"{float(value):.2f}")
                except Exception:
                    value_label.setText(str(value))

                value_label.setObjectName("channelDRValue")
                value_label.setAlignment(Qt.AlignmentFlag.AlignRight)

                row.addWidget(channel_label)
                row.addStretch(1)
                row.addWidget(value_label)
                layout.addLayout(row)

        chart_button = QPushButton("Dynamic Range Chart...")
        chart_button.clicked.connect(self.open_chart)
        layout.addWidget(chart_button)

        close_button = QPushButton("Close")
        close_button.setFixedWidth(88)
        close_button.clicked.connect(self.accept)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_row.addWidget(close_button)
        close_row.addStretch(1)
        layout.addLayout(close_row)

    def open_chart(self):
        self.show_chart_callback()


# ============================================================
# Report view
# ============================================================


class ReportView(QWidget):
    def __init__(self, result, parent=None):
        super().__init__(parent)

        self.result = result
        self.png_data = result["png_data"]

        self.original_pixmap = QPixmap()

        loaded = self.original_pixmap.loadFromData(
            self.png_data,
            "PNG",
        )

        if not loaded:
            raise RuntimeError(
                "The generated MasVis PNG could not be loaded."
            )

        self.current_width = ORIGINAL_VIEW_WIDTH

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("reportScroll")

        self.image_label = QLabel()
        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignHCenter
        )
        self.image_label.setObjectName("reportImage")

        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

        self.set_report_width(ORIGINAL_VIEW_WIDTH)

    @property
    def maximum_sharp_width(self):
        return self.original_pixmap.width()

    def set_report_width(self, width):
        width = int(width)
        width = max(
            600,
            min(width, self.maximum_sharp_width),
        )

        self.current_width = width

        scaled = self.original_pixmap.scaledToWidth(
            width,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(scaled)
        self.image_label.setFixedSize(scaled.size())

    def zoom_by(self, delta):
        self.set_report_width(self.current_width + delta)

    def original_size(self):
        self.set_report_width(ORIGINAL_VIEW_WIDTH)

    def fit_to_window(self):
        width = self.scroll_area.viewport().width() - 24

        if width <= 0:
            return

        self.set_report_width(
            min(width, self.maximum_sharp_width)
        )


# ============================================================
# Overview view
# ============================================================


class OverviewView(QWidget):
    def __init__(self, result, parent=None):
        super().__init__(parent)

        self.result = result
        self.png_data = result["png_data"]

        self.original_pixmap = QPixmap()

        if not self.original_pixmap.loadFromData(
            self.png_data,
            "PNG",
        ):
            raise RuntimeError(
                "The generated MasVis overview PNG could not be loaded."
            )

        self.current_width = min(
            OVERVIEW_VIEW_WIDTH,
            self.original_pixmap.width(),
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("reportScroll")

        self.image_label = QLabel()
        self.image_label.setObjectName("reportImage")
        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignHCenter
        )

        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)

        self.set_report_width(self.current_width)

    @property
    def maximum_sharp_width(self):
        return self.original_pixmap.width()

    def set_report_width(self, width):
        width = int(width)
        width = max(
            600,
            min(width, self.maximum_sharp_width),
        )

        self.current_width = width

        scaled = self.original_pixmap.scaledToWidth(
            width,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(scaled)
        self.image_label.setFixedSize(scaled.size())

    def zoom_by(self, delta):
        self.set_report_width(self.current_width + delta)

    def original_size(self):
        self.set_report_width(
            min(
                OVERVIEW_VIEW_WIDTH,
                self.maximum_sharp_width,
            )
        )

    def fit_to_window(self):
        width = self.scroll_area.viewport().width() - 24

        if width <= 0:
            return

        self.set_report_width(
            min(width, self.maximum_sharp_width)
        )


# ============================================================
# Compare / GIF export
# ============================================================


def export_entries_to_gif(
    entries,
    output_path,
    frame_width=GIF_FRAME_WIDTH,
    duration_ms=GIF_FRAME_DURATION_MS,
):
    """
    Export selected result tabs as an animated GIF.

    Frames come from the already-generated report PNGs. They are scaled to
    one width and centered on a shared report-colour canvas so detailed
    reports and Overview tabs can coexist safely in the same animation.
    """

    if len(entries) < 2:
        raise ValueError(
            "At least two result tabs are required."
        )

    frames = []

    for entry in entries:
        with Image.open(
            io.BytesIO(entry["png_data"])
        ) as source:
            frame = source.convert("RGB")

            if frame.width != frame_width:
                scale = (
                    float(frame_width)
                    / float(frame.width)
                )

                target_height = max(
                    1,
                    int(
                        round(
                            frame.height
                            * scale
                        )
                    ),
                )

                frame = frame.resize(
                    (
                        frame_width,
                        target_height,
                    ),
                    Image.Resampling.LANCZOS,
                )

            frames.append(
                frame.copy()
            )

    if len(frames) < 2:
        raise ValueError(
            "Could not create at least two GIF frames."
        )

    canvas_width = max(
        frame.width
        for frame in frames
    )
    canvas_height = max(
        frame.height
        for frame in frames
    )

    normalized = []

    for frame in frames:
        canvas = Image.new(
            "RGB",
            (
                canvas_width,
                canvas_height,
            ),
            frame.getpixel((0, 0)),
        )

        x = (
            canvas_width
            - frame.width
        ) // 2

        canvas.paste(
            frame,
            (
                x,
                0,
            ),
        )

        normalized.append(
            canvas
        )

    output_path = Path(
        output_path
    )

    if output_path.suffix.lower() != ".gif":
        output_path = output_path.with_suffix(
            ".gif"
        )

    normalized[0].save(
        output_path,
        format="GIF",
        save_all=True,
        append_images=normalized[1:],
        duration=int(duration_ms),
        loop=0,
        optimize=False,
        disposal=2,
    )

    return output_path


class CompareSelectionDialog(QDialog):
    def __init__(
        self,
        entries,
        gif_duration_ms=GIF_FRAME_DURATION_MS,
        gif_frame_width=GIF_FRAME_WIDTH,
        parent=None,
    ):
        super().__init__(parent)

        self.entries = list(entries)
        self.gif_duration_ms = max(1000, int(gif_duration_ms))
        self.gif_frame_width = max(300, int(gif_frame_width))
        self.selected_entries = []
        self.action_mode = "visual"
        self.checkboxes = []

        self.setWindowTitle("Compare Tabs")
        self.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        self.setFixedSize(
            700,
            430,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        layout.setSpacing(12)

        hint = QLabel(
            "Select tabs to compare. Dynamics Comparison requires exactly two detailed reports."
        )
        hint.setObjectName(
            "compareHint"
        )
        layout.addWidget(
            hint
        )

        scroll = QScrollArea()
        scroll.setObjectName(
            "compareScroll"
        )
        scroll.setWidgetResizable(
            True
        )

        body = QWidget()
        body.setObjectName(
            "compareListBody"
        )

        body_layout = QVBoxLayout(
            body
        )
        body_layout.setContentsMargins(
            8,
            4,
            8,
            4,
        )
        body_layout.setSpacing(0)

        for entry in self.entries:
            row = QFrame()
            row.setObjectName(
                "compareRow"
            )

            row_layout = QVBoxLayout(
                row
            )
            row_layout.setContentsMargins(
                8,
                8,
                8,
                8,
            )
            row_layout.setSpacing(3)

            checkbox = QCheckBox(
                entry["title"]
            )
            checkbox.setToolTip(
                entry["tooltip"]
            )
            checkbox.stateChanged.connect(
                self.update_selected_state
            )

            path_label = QLabel(
                entry["subtitle"]
            )
            path_label.setObjectName(
                "comparePath"
            )
            path_label.setToolTip(
                entry["tooltip"]
            )
            path_label.setTextInteractionFlags(
                Qt.TextInteractionFlag
                .TextSelectableByMouse
            )

            row_layout.addWidget(
                checkbox
            )
            row_layout.addWidget(
                path_label
            )

            body_layout.addWidget(
                row
            )

            self.checkboxes.append(
                (
                    checkbox,
                    entry,
                )
            )

        body_layout.addStretch(1)

        scroll.setWidget(
            body
        )
        layout.addWidget(
            scroll,
            1,
        )

        # Action toolbar: visual report compare first, then the dynamics
        # analysis and GIF export as clearly separated semantic groups.
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(0, 0, 0, 0)
        action_bar.setSpacing(6)

        self.compare_selected_button = QPushButton(
            "Compare"
        )
        self.compare_selected_button.setEnabled(
            False
        )
        self.compare_selected_button.setToolTip(
            "Compare the selected report tabs side by side"
        )
        self.compare_selected_button.clicked.connect(
            self.accept_selected
        )

        compare_all_button = QPushButton(
            "Compare All"
        )
        compare_all_button.setToolTip(
            "Compare all report tabs side by side"
        )
        compare_all_button.clicked.connect(
            self.accept_all
        )

        self.dynamics_compare_button = QPushButton(
            "Dynamics Comparison"
        )
        self.dynamics_compare_button.setEnabled(False)
        self.dynamics_compare_button.setToolTip(
            "Analyze measured DR and aligned Short-Term loudness dynamics of exactly two detailed reports"
        )
        self.dynamics_compare_button.clicked.connect(
            self.accept_dynamics
        )

        self.export_gif_button = QPushButton(
            "Export GIF..."
        )
        self.export_gif_button.setEnabled(
            False
        )
        self.export_gif_button.setToolTip(
            "Export the selected tabs as an animated GIF"
        )
        self.export_gif_button.clicked.connect(
            self.export_gif
        )

        dialog_dark = bool(
            getattr(
                parent,
                "system_dark",
                detect_system_dark(QApplication.instance()),
            )
        )
        self.compare_selected_button.setIcon(
            load_fluent_icon("compare", dialog_dark)
        )
        compare_all_button.setIcon(
            load_fluent_icon("compare_all", dialog_dark)
        )
        self.dynamics_compare_button.setIcon(
            load_fluent_icon("assessment", dialog_dark)
        )
        self.export_gif_button.setIcon(
            load_fluent_icon("gif", dialog_dark)
        )

        for button in (
            self.compare_selected_button,
            compare_all_button,
            self.dynamics_compare_button,
            self.export_gif_button,
        ):
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(34)

        action_bar.addWidget(
            self.compare_selected_button
        )
        action_bar.addWidget(
            compare_all_button
        )
        action_bar.addSpacing(10)
        action_bar.addWidget(
            self.dynamics_compare_button
        )
        action_bar.addSpacing(10)
        action_bar.addWidget(
            self.export_gif_button
        )
        action_bar.addStretch(1)

        # Keep the actions at the top where they read like a compact toolbar
        # instead of a row of unrelated footer buttons.
        layout.insertLayout(
            1,
            action_bar,
        )

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addStretch(1)

        cancel_button = QPushButton(
            "Cancel"
        )
        cancel_button.clicked.connect(
            self.reject
        )
        footer.addWidget(
            cancel_button
        )

        layout.addLayout(
            footer
        )

    def checked_entries(self):
        return [
            entry
            for checkbox, entry
            in self.checkboxes
            if checkbox.isChecked()
        ]

    def update_selected_state(self):
        selected_count = len(
            self.checked_entries()
        )

        enabled = (
            selected_count >= 2
        )

        self.compare_selected_button.setEnabled(
            enabled
        )
        self.export_gif_button.setEnabled(
            enabled
        )

        selected = self.checked_entries()
        dynamics_enabled = (
            len(selected) == 2
            and all(entry.get("dynamics_capable") for entry in selected)
        )
        self.dynamics_compare_button.setEnabled(
            dynamics_enabled
        )

    def accept_dynamics(self):
        selected = self.checked_entries()

        if (
            len(selected) != 2
            or not all(entry.get("dynamics_capable") for entry in selected)
        ):
            QMessageBox.information(
                self,
                "Cannot Compare Dynamics",
                "Select exactly two detailed report tabs.",
            )
            return

        self.selected_entries = selected
        self.action_mode = "dynamics"
        self.accept()

    def accept_selected(self):
        selected = (
            self.checked_entries()
        )

        if len(selected) < 2:
            QMessageBox.information(
                self,
                "Cannot Compare",
                "Select at least two tabs.",
            )
            return

        self.selected_entries = (
            selected
        )
        self.action_mode = "visual"
        self.accept()

    def accept_all(self):
        if len(self.entries) < 2:
            return

        self.selected_entries = list(
            self.entries
        )
        self.action_mode = "visual"
        self.accept()

    def export_gif(self):
        selected = self.checked_entries()

        if len(selected) < 2:
            QMessageBox.information(
                self,
                "Cannot Export GIF",
                "Select at least two tabs first.",
            )
            return

        default_path = _existing_directory(
            getattr(self.parent(), "preferences", {}).get("gif_directory")
            if hasattr(self.parent(), "preferences") else None
        ) / "MasVis Comparison.gif"
        initial_quality = next(
            (
                name
                for name, width in GIF_RESOLUTION_WIDTHS.items()
                if width == self.gif_frame_width
            ),
            "High",
        )
        initial_duration = max(1, int(round(self.gif_duration_ms / 1000.0)))

        dialog, quality_combo, duration_spin = _gif_save_dialog(
            self,
            default_path,
            initial_quality,
            initial_duration,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_files = dialog.selectedFiles()
        if not selected_files:
            return

        output_path = selected_files[0]
        gif_resolution = quality_combo.currentData() or "High"
        gif_duration_seconds = duration_spin.value()
        self.gif_frame_width = GIF_RESOLUTION_WIDTHS.get(gif_resolution, 810)
        self.gif_duration_ms = int(gif_duration_seconds) * 1000

        # Persist only as last-used export defaults. They are intentionally no
        # longer part of the Preferences dialog.
        main_window = self.parent()
        if hasattr(main_window, "preferences") and hasattr(main_window, "save_preferences"):
            main_window.preferences["gif_resolution"] = gif_resolution
            main_window.preferences["gif_duration"] = gif_duration_seconds
            main_window.preferences["gif_directory"] = str(Path(output_path).parent)
            main_window.save_preferences()

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            export_entries_to_gif(
                selected,
                output_path,
                frame_width=self.gif_frame_width,
                duration_ms=self.gif_duration_ms,
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "GIF Export Error",
                str(exc),
            )
            return

        finally:
            QApplication.restoreOverrideCursor()



class ComparisonWindow(QMainWindow):
    def __init__(
        self,
        entries,
        comparison_number,
        plot_width=COMPARISON_PLOT_WIDTH,
        on_plot_width_changed=None,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.entries = list(
            entries
        )
        self.report_items = []

        self.base_plot_width = max(COMPARISON_MIN_PLOT_WIDTH, min(int(plot_width), 1080))
        self.current_plot_width = self.base_plot_width
        self.maximum_sharp_width = self.base_plot_width
        self.on_plot_width_changed = on_plot_width_changed

        self.setWindowTitle(
            f"Comparison #{comparison_number}"
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        if APP_ICON.is_file():
            self.setWindowIcon(
                QIcon(str(APP_ICON))
            )

        screen = (
            QApplication.primaryScreen()
        )

        if screen is not None:
            available = (
                screen.availableGeometry()
            )
            screen_width = (
                available.width()
            )
            screen_height = (
                available.height()
            )
        else:
            screen_width = 1920
            screen_height = 1080

        proposed_width = (
            min(
                len(self.entries),
                2,
            )
            * self.base_plot_width
            + 46
        )

        initial_width = min(
            max(
                900,
                proposed_width,
            ),
            max(
                900,
                screen_width - 80,
            ),
        )

        initial_height = min(
            760,
            max(
                620,
                screen_height - 100,
            ),
        )

        self.resize(
            initial_width,
            initial_height,
        )
        self.setMinimumSize(
            760,
            560,
        )

        self.comparison_root = QWidget()
        self.comparison_root.setObjectName(
            "contentArea"
        )

        root_layout = QVBoxLayout(
            self.comparison_root
        )
        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root_layout.setSpacing(0)

        self.comparison_scroll = QScrollArea()
        self.comparison_scroll.setObjectName(
            "reportScroll"
        )
        self.comparison_scroll.setWidgetResizable(
            False
        )
        self.comparison_scroll.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop
        )
        self.comparison_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        root_layout.addWidget(
            self.comparison_scroll
        )

        self.content = QWidget()
        self.content.setObjectName(
            "comparisonContent"
        )

        self.content_layout = QHBoxLayout(
            self.content
        )
        self.content_layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )
        self.content_layout.setSpacing(
            10
        )
        self.content_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )

        original_widths = []

        for entry in self.entries:
            pixmap = QPixmap()

            if not pixmap.loadFromData(
                entry["png_data"],
                "PNG",
            ):
                continue

            image = QLabel()
            image.setAlignment(
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignHCenter
            )
            image.setToolTip(
                entry["tooltip"]
            )
            image.setObjectName(
                "reportImage"
            )

            holder = QWidget()
            holder_layout = QVBoxLayout(
                holder
            )
            holder_layout.setContentsMargins(
                0,
                0,
                0,
                0,
            )
            holder_layout.setSpacing(0)
            holder_layout.addWidget(
                image,
                0,
                Qt.AlignmentFlag.AlignTop,
            )

            self.content_layout.addWidget(
                holder,
                0,
                Qt.AlignmentFlag.AlignTop,
            )

            self.report_items.append(
                {
                    "pixmap": pixmap,
                    "label": image,
                    "holder": holder,
                }
            )

            original_widths.append(
                pixmap.width()
            )

        if original_widths:
            self.maximum_sharp_width = min(
                original_widths
            )

        self.comparison_scroll.setWidget(
            self.content
        )

        self.zoom_frame = QFrame(
            self.comparison_root
        )
        self.zoom_frame.setObjectName(
            "zoomFrame"
        )

        zoom_layout = QHBoxLayout(
            self.zoom_frame
        )
        zoom_layout.setContentsMargins(
            3,
            3,
            3,
            3,
        )
        zoom_layout.setSpacing(0)

        self.zoom_out_button = QPushButton(
            "−"
        )
        self.zoom_out_button.setObjectName(
            "zoomOutButton"
        )
        self.zoom_out_button.setToolTip(
            "Zoom Out"
        )
        self.zoom_out_button.clicked.connect(
            lambda:
            self.zoom_by(-100)
        )

        self.zoom_original_button = QPushButton(
            "1:1"
        )
        self.zoom_original_button.setToolTip(
            "Restore the width this comparison opened with"
        )
        self.zoom_original_button.clicked.connect(
            self.original_size
        )

        self.zoom_indicator = QPushButton(
            str(
                self.base_plot_width
            )
        )
        self.zoom_indicator.setObjectName(
            "zoomIndicator"
        )
        self.zoom_indicator.setToolTip(
            "Current width of each comparison report [px]"
        )
        self.zoom_indicator.setEnabled(
            False
        )

        self.zoom_fit_button = QPushButton(
            "↔"
        )
        self.zoom_fit_button.setToolTip(
            "Fit comparison group to window width"
        )
        self.zoom_fit_button.clicked.connect(
            self.fit_to_window
        )

        self.zoom_in_button = QPushButton(
            "+"
        )
        self.zoom_in_button.setObjectName(
            "zoomInButton"
        )
        self.zoom_in_button.setToolTip(
            "Zoom In"
        )
        self.zoom_in_button.clicked.connect(
            lambda:
            self.zoom_by(100)
        )

        for button in (
            self.zoom_out_button,
            self.zoom_original_button,
            self.zoom_indicator,
            self.zoom_fit_button,
            self.zoom_in_button,
        ):
            button.setFixedHeight(
                30
            )
            button.setMinimumWidth(
                45
            )
            zoom_layout.addWidget(
                button
            )

        self.zoom_frame.adjustSize()

        self.setCentralWidget(
            self.comparison_root
        )

        self._initial_horizontal_center_done = False

        self.set_plot_width(
            self.base_plot_width,
            preserve_scroll=False,
        )

    def scrollbar_ratio(
        self,
        bar,
    ):
        maximum = bar.maximum()
        minimum = bar.minimum()

        if maximum <= minimum:
            return 0.5

        return (
            float(
                bar.value()
                - minimum
            )
            / float(
                maximum
                - minimum
            )
        )

    def restore_scroll_ratios(
        self,
        horizontal_ratio,
        vertical_ratio,
    ):
        hbar = (
            self.comparison_scroll
            .horizontalScrollBar()
        )
        vbar = (
            self.comparison_scroll
            .verticalScrollBar()
        )

        hbar.setValue(
            int(
                round(
                    hbar.minimum()
                    + horizontal_ratio
                    * (
                        hbar.maximum()
                        - hbar.minimum()
                    )
                )
            )
        )

        vbar.setValue(
            int(
                round(
                    vbar.minimum()
                    + vertical_ratio
                    * (
                        vbar.maximum()
                        - vbar.minimum()
                    )
                )
            )
        )

    def set_plot_width(
        self,
        width,
        preserve_scroll=True,
    ):
        if not self.report_items:
            return

        hbar = (
            self.comparison_scroll
            .horizontalScrollBar()
        )
        vbar = (
            self.comparison_scroll
            .verticalScrollBar()
        )

        horizontal_ratio = self.scrollbar_ratio(
            hbar
        )
        vertical_ratio = self.scrollbar_ratio(
            vbar
        )

        width = max(
            COMPARISON_MIN_PLOT_WIDTH,
            min(
                int(width),
                self.maximum_sharp_width,
            ),
        )

        self.current_plot_width = width

        if self.on_plot_width_changed is not None:
            try:
                self.on_plot_width_changed(width)
            except Exception:
                pass

        max_height = 0

        for item in self.report_items:
            scaled = (
                item["pixmap"]
                .scaledToWidth(
                    width,
                    Qt.TransformationMode
                    .SmoothTransformation,
                )
            )

            item["label"].setPixmap(
                scaled
            )
            item["label"].setFixedSize(
                scaled.size()
            )
            item["holder"].setFixedSize(
                scaled.size()
            )

            max_height = max(
                max_height,
                scaled.height(),
            )

        count = len(
            self.report_items
        )

        content_width = (
            count
            * width
            + max(
                0,
                count - 1,
            )
            * self.content_layout.spacing()
            + 20
        )

        self.content.setFixedSize(
            max(
                content_width,
                1,
            ),
            max(
                max_height + 20,
                1,
            ),
        )

        self.zoom_indicator.setText(
            str(width)
        )

        self.zoom_frame.adjustSize()
        self.position_zoom_overlay()

        if preserve_scroll:
            QTimer.singleShot(
                0,
                lambda:
                self.restore_scroll_ratios(
                    horizontal_ratio,
                    vertical_ratio,
                ),
            )

    def zoom_by(
        self,
        delta,
    ):
        self.set_plot_width(
            self.current_plot_width
            + int(delta)
        )

    def original_size(self):
        self.set_plot_width(
            self.base_plot_width,
            preserve_scroll=False,
        )

        QTimer.singleShot(
            0,
            self.center_horizontal_scroll,
        )

    def fit_to_window(self):
        count = len(
            self.report_items
        )

        if count <= 0:
            return

        viewport_width = (
            self.comparison_scroll
            .viewport()
            .width()
        )

        available = (
            viewport_width
            - 20
            - max(
                0,
                count - 1,
            )
            * self.content_layout.spacing()
        )

        if available <= 0:
            return

        width = int(
            available / count
        )

        width = max(
            COMPARISON_MIN_PLOT_WIDTH,
            min(
                width,
                self.maximum_sharp_width,
            ),
        )

        self.set_plot_width(
            width,
            preserve_scroll=False,
        )

        QTimer.singleShot(
            0,
            self.center_horizontal_scroll,
        )

    def center_horizontal_scroll(self):
        bar = (
            self.comparison_scroll
            .horizontalScrollBar()
        )

        if bar.maximum() > bar.minimum():
            bar.setValue(
                (
                    bar.minimum()
                    + bar.maximum()
                )
                // 2
            )

    def position_zoom_overlay(self):
        self.zoom_frame.adjustSize()

        x = max(
            8,
            (
                self.comparison_root.width()
                - self.zoom_frame.width()
            )
            // 2,
        )

        y = max(
            8,
            self.comparison_root.height()
            - self.zoom_frame.height()
            - 12,
        )

        self.zoom_frame.move(
            x,
            y,
        )
        self.zoom_frame.raise_()

    def resizeEvent(
        self,
        event,
    ):
        super().resizeEvent(
            event
        )
        self.position_zoom_overlay()

    def showEvent(
        self,
        event,
    ):
        super().showEvent(
            event
        )
        self.position_zoom_overlay()

        if not self._initial_horizontal_center_done:
            self._initial_horizontal_center_done = True

            QTimer.singleShot(
                0,
                self.center_horizontal_scroll,
            )


# ============================================================
# Main window
# ============================================================


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.analysis_thread = None
        self.analysis_worker = None
        self.processing_dialog = None
        self.dynamics_compare_thread = None
        self.dynamics_compare_worker = None
        self.dynamics_compare_progress = None
        self.close_after_cancel = False
        self.system_dark = True

        self.settings = QSettings()
        self.default_app_font = QFont(QApplication.instance().font())
        self.preferences = self.load_preferences()

        self.comparison_counter = 0
        self.comparison_windows = []
        self.was_maximized_before_fullscreen = False

        self.setWindowTitle(
            APP_NAME
        )

        self.resize(1080, 720)
        self.setMinimumSize(850, 600)
        self.setAcceptDrops(True)

        if APP_ICON.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON)))

        self.build_ui()
        self.build_actions()
        self.apply_app_font()
        self.apply_system_theme()

        try:
            QApplication.instance().styleHints().colorSchemeChanged.connect(
                self.on_system_color_scheme_changed
            )
        except Exception:
            pass

    # --------------------------------------------------------
    # Theme
    # --------------------------------------------------------

    def load_preferences(self):
        return {
            "appearance": self.settings.value(
                "appearance", "System", type=str
            ),
            "app_font": self.settings.value(
                "app_font", "", type=str
            ),
            "report_font": self.settings.value(
                "report_font", "", type=str
            ),
            "report_theme": self.settings.value(
                "report_theme", "Light", type=str
            ),
            "report_quality": self.settings.value(
                "report_quality", "High", type=str
            ),
            "save_format": self.settings.value(
                "save_format", "PNG", type=str
            ),
            "export_resolution": self.settings.value(
                "export_resolution",
                self.settings.value("export_quality", "High", type=str),
                type=str,
            ),
            "comparison_width": int(
                self.settings.value("comparison_width", 606)
            ),
            "gif_resolution": self.settings.value(
                "gif_resolution",
                self.settings.value("gif_quality", "High", type=str),
                type=str,
            ),
            "gif_duration": int(
                self.settings.value("gif_duration", 3)
            ),
            "open_directory": self.settings.value(
                "open_directory", str(Path.home()), type=str
            ),
            "save_directory": self.settings.value(
                "save_directory", str(Path.home()), type=str
            ),
            "gif_directory": self.settings.value(
                "gif_directory", str(Path.home()), type=str
            ),
        }

    def save_preferences(self):
        for key, value in self.preferences.items():
            self.settings.setValue(key, value)

        self.settings.sync()

    def apply_app_font(self):
        app = QApplication.instance()
        custom = qfont_from_string(
            self.preferences.get("app_font", "")
        )

        if custom is None:
            font = QFont(self.default_app_font)
        else:
            font = QFont(custom)

        app.setFont(font)
        self.refresh_widget_fonts(font)

    def refresh_widget_fonts(self, font):
        preserve_names = {
            "zoomIndicator",
            "processingCounter",
            "channelDRValue",
        }

        app = QApplication.instance()

        for widget in app.allWidgets():
            if widget.objectName() in preserve_names:
                continue

            widget.setFont(font)
            widget.update()

    def apply_system_theme(self):
        app = QApplication.instance()
        appearance = self.preferences.get("appearance", "System")

        if appearance == "Light":
            self.system_dark = False
        elif appearance == "Dark":
            self.system_dark = True
        else:
            self.system_dark = detect_system_dark(app)

        app.setStyleSheet(build_stylesheet(self.system_dark))
        self.refresh_toolbar_icons()

    def on_system_color_scheme_changed(self, scheme):
        if self.preferences.get("appearance", "System") == "System":
            self.apply_system_theme()

    def report_render_scale(self):
        quality = self.preferences.get("report_quality", "High")
        return REPORT_QUALITY_SCALES.get(quality, 3)

    def show_preferences(self):
        dialog = PreferencesDialog(
            self.preferences,
            self.default_app_font,
            self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Preferences owns only persistent application/report settings.
        # Export choices and Compare width are remembered from their own UI
        # and stay available as last-used defaults without cluttering this dialog.
        self.preferences.update(dialog.configuration())
        self.save_preferences()
        self.apply_app_font()
        self.apply_system_theme()


    def refresh_toolbar_icons(self):
        self.open_button.setIcon(
            load_fluent_icon(
                "open",
                self.system_dark,
            )
        )

        self.advanced_button.setIcon(
            load_fluent_icon(
                "advanced",
                self.system_dark,
            )
        )

        self.save_button.setIcon(
            load_fluent_icon(
                "save",
                self.system_dark,
            )
        )

        self.save_all_button.setIcon(
            load_fluent_icon(
                "save_all",
                self.system_dark,
            )
        )

        self.compare_button.setIcon(
            load_fluent_icon(
                "compare",
                self.system_dark,
            )
        )

        self.play_button.setIcon(
            load_fluent_icon(
                "play",
                self.system_dark,
            )
        )

        self.assessment_button.setIcon(
            load_fluent_icon(
                "assessment",
                self.system_dark,
            )
        )

        self.preferences_button.setIcon(
            load_fluent_icon(
                "settings",
                self.system_dark,
            )
        )

        self.file_info_button.setIcon(
            load_fluent_icon(
                "file_info",
                self.system_dark,
            )
        )

        self.help_button.setIcon(
            load_fluent_icon(
                "help",
                self.system_dark,
            )
        )

        self.about_button.setIcon(
            load_fluent_icon(
                "about",
                self.system_dark,
            )
        )

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):
        self.root = QWidget()
        self.root.setObjectName("root")

        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # GTK-inspired compact headerbar, translated into a Windows
        # desktop interaction model: visible icon actions, no hamburger,
        # no duplicate application title.
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(52)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(4)

        # Left side: file actions
        self.open_button = self.create_header_icon_button(
            "Open Files"
        )
        self.open_button.clicked.connect(self.open_files)

        self.advanced_button = self.create_header_icon_button(
            "Advanced Open"
        )
        self.advanced_button.clicked.connect(
            self.show_advanced_open
        )

        self.save_button = self.create_header_icon_button(
            "Save Current Tab"
        )
        self.save_button.clicked.connect(self.save_current)
        self.save_button.setEnabled(False)

        self.save_all_button = self.create_header_icon_button(
            "Save All Tabs"
        )
        self.save_all_button.clicked.connect(self.save_all)
        self.save_all_button.setEnabled(False)

        self.play_button = self.create_header_icon_button(
            "Play current file using the default audio player configured in Windows.\n"
            "MasVis only opens the file in that external app; it does not play audio itself."
        )
        self.play_button.clicked.connect(
            self.play_current_file
        )
        self.play_button.setEnabled(False)

        header_layout.addWidget(self.open_button)
        header_layout.addWidget(self.advanced_button)
        header_layout.addWidget(self.save_button)
        header_layout.addWidget(self.save_all_button)
        header_layout.addWidget(self.play_button)

        header_layout.addStretch(1)

        # Right side: analysis/navigation actions
        self.dr_button = QPushButton("00.0")
        self.dr_button.setObjectName("drButton")
        self.dr_button.setFixedSize(56, 36)
        self.dr_button.setToolTip(
            "Dynamic Range - click for details"
        )
        self.dr_button.clicked.connect(
            self.show_dr_details
        )
        self.dr_button.setVisible(False)

        self.assessment_button = self.create_header_icon_button(
            "Dynamics Assessment"
        )
        self.assessment_button.clicked.connect(
            self.show_dynamics_assessment
        )
        self.assessment_button.setEnabled(False)

        self.compare_button = self.create_header_icon_button(
            "Compare"
        )
        self.compare_button.clicked.connect(
            self.show_compare
        )
        self.compare_button.setEnabled(False)

        self.preferences_button = self.create_header_icon_button(
            "Preferences"
        )
        self.preferences_button.clicked.connect(
            self.show_preferences
        )

        self.file_info_button = self.create_header_icon_button(
            "File Information"
        )
        self.file_info_button.clicked.connect(
            self.show_file_information
        )
        self.file_info_button.setEnabled(False)

        # Help remains a compact drop-down for the manual and
        # keyboard-shortcut reference. Supported formats belong in
        # README/release documentation rather than a dedicated UI dialog.
        self.help_button = self.create_header_icon_button(
            "Help"
        )
        self.help_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )

        self.help_menu = QMenu(self.help_button)

        help_action = self.help_menu.addAction("Help")
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self.show_help)

        shortcuts_action = self.help_menu.addAction(
            "Keyboard Shortcuts"
        )
        shortcuts_action.triggered.connect(
            self.show_shortcuts
        )

        self.help_button.setMenu(self.help_menu)

        self.about_button = self.create_header_icon_button(
            "About"
        )
        self.about_button.clicked.connect(self.show_about)

        header_layout.addWidget(self.dr_button)
        header_layout.addSpacing(10)

        # Keep every icon action on the right at the same spacing.  The DR
        # meter is the only deliberately separated element because it is a
        # numeric status badge rather than another icon action.
        right_actions = QHBoxLayout()
        right_actions.setContentsMargins(0, 0, 0, 0)
        right_actions.setSpacing(4)
        right_actions.addWidget(self.assessment_button)
        right_actions.addWidget(self.compare_button)
        right_actions.addWidget(self.file_info_button)
        right_actions.addWidget(self.preferences_button)
        right_actions.addWidget(self.help_button)
        right_actions.addWidget(self.about_button)
        header_layout.addLayout(right_actions)

        root_layout.addWidget(self.header)

        # ----------------------------------------------------
        # Content / tabs
        # ----------------------------------------------------

        self.content_area = QWidget()
        self.content_area.setObjectName("contentArea")

        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.empty_page = QLabel(
            "Open one or more audio files\n"
            "or drag & drop them into this window"
        )
        self.empty_page.setObjectName("emptyPage")
        self.empty_page.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.tabs = QTabWidget()
        self.tabs.setObjectName("reportTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.currentChanged.connect(
            self.on_tab_changed
        )
        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )
        self.tabs.setVisible(False)

        content_layout.addWidget(self.empty_page, 1)
        content_layout.addWidget(self.tabs, 1)

        root_layout.addWidget(self.content_area, 1)

        # ----------------------------------------------------
        # Floating zoom control
        # ----------------------------------------------------

        self.zoom_frame = QFrame(self.content_area)
        self.zoom_frame.setObjectName("zoomFrame")

        zoom_layout = QHBoxLayout(self.zoom_frame)
        zoom_layout.setContentsMargins(3, 3, 3, 3)
        zoom_layout.setSpacing(0)

        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setObjectName("zoomOutButton")
        self.zoom_out_button.setToolTip("Zoom Out")
        self.zoom_out_button.clicked.connect(
            lambda:
            self.zoom_current(-100)
        )

        self.zoom_original_button = QPushButton("1:1")
        self.zoom_original_button.setToolTip(
            "Restore original report dimensions"
        )
        self.zoom_original_button.clicked.connect(
            self.zoom_original
        )

        self.zoom_indicator = QPushButton("1080")
        self.zoom_indicator.setObjectName("zoomIndicator")
        self.zoom_indicator.setToolTip(
            "Current report width [px]"
        )
        self.zoom_indicator.setEnabled(False)

        self.zoom_fit_button = QPushButton("↔")
        self.zoom_fit_button.setToolTip(
            "Scale to Window Width"
        )
        self.zoom_fit_button.clicked.connect(
            self.fit_current
        )

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_in_button.setToolTip("Zoom In")
        self.zoom_in_button.clicked.connect(
            lambda:
            self.zoom_current(100)
        )

        for button in (
            self.zoom_out_button,
            self.zoom_original_button,
            self.zoom_indicator,
            self.zoom_fit_button,
            self.zoom_in_button,
        ):
            button.setFixedHeight(30)
            button.setMinimumWidth(45)
            zoom_layout.addWidget(button)

        self.zoom_frame.adjustSize()
        self.zoom_frame.setVisible(False)

        self.setCentralWidget(self.root)

    def create_header_icon_button(self, tooltip):
        button = QToolButton()
        button.setObjectName("headerIconButton")
        button.setFixedSize(HEADER_BUTTON_SIZE, HEADER_BUTTON_SIZE)
        button.setIconSize(QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        button.setToolTip(tooltip)
        return button

    # --------------------------------------------------------
    # Keyboard actions
    # --------------------------------------------------------

    def build_actions(self):
        actions = [
            (
                QKeySequence.StandardKey.Open,
                self.open_files,
            ),
            (
                QKeySequence("Shift+O"),
                self.show_advanced_open,
            ),
            (
                QKeySequence.StandardKey.Save,
                self.save_current,
            ),
            (
                QKeySequence("Ctrl+Shift+S"),
                self.save_all,
            ),
            (
                QKeySequence("Ctrl+I"),
                self.show_file_information,
            ),
            (
                QKeySequence("Ctrl+G"),
                self.show_compare,
            ),
            (
                QKeySequence("Ctrl++"),
                lambda:
                self.zoom_current(100),
            ),
            (
                QKeySequence("Ctrl+-"),
                lambda:
                self.zoom_current(-100),
            ),
            (
                QKeySequence("Ctrl+0"),
                self.zoom_original,
            ),
            (
                QKeySequence("Ctrl+W"),
                self.close_current_tab,
            ),
            (
                QKeySequence("Ctrl+Tab"),
                lambda:
                self.cycle_tab(1),
            ),
            (
                QKeySequence("Ctrl+Shift+Tab"),
                lambda:
                self.cycle_tab(-1),
            ),
            (
                QKeySequence("Ctrl+,"),
                self.show_preferences,
            ),
            (
                QKeySequence("Ctrl+?"),
                self.show_shortcuts,
            ),
            (
                QKeySequence("F11"),
                self.toggle_fullscreen,
            ),
            (
                QKeySequence("Escape"),
                self.leave_fullscreen,
            ),
            (
                QKeySequence("F1"),
                self.show_help,
            ),
            (
                QKeySequence("Ctrl+Q"),
                self.close,
            ),
        ]

        for shortcut, callback in actions:
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)

    # --------------------------------------------------------
    # Window / tab shortcuts
    # --------------------------------------------------------

    def close_current_tab(self):
        index = self.tabs.currentIndex()

        if index >= 0:
            self.close_tab(index)

    def cycle_tab(self, direction):
        count = self.tabs.count()

        if count <= 1:
            return

        current = self.tabs.currentIndex()

        self.tabs.setCurrentIndex(
            (current + int(direction))
            % count
        )

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.leave_fullscreen()
            return

        self.was_maximized_before_fullscreen = (
            self.isMaximized()
        )
        self.showFullScreen()

    def leave_fullscreen(self):
        if not self.isFullScreen():
            return

        if self.was_maximized_before_fullscreen:
            self.showMaximized()
        else:
            self.showNormal()

    # --------------------------------------------------------
    # Current tab
    # --------------------------------------------------------

    def current_report(self):
        widget = self.tabs.currentWidget()

        if isinstance(widget, ReportView):
            return widget

        return None

    def play_current_file(self):
        """Open the current analyzed file with Windows' configured default app."""
        report = self.current_report()
        if report is None:
            return

        path = Path(report.result["path"])

        if not path.is_file():
            QMessageBox.warning(
                self,
                "Audio file not found",
                (
                    "The analyzed audio file is no longer available at its original location.\n\n"
                    f"{path}"
                ),
            )
            return

        try:
            if hasattr(os, "startfile"):
                # On Windows, startfile delegates the Open action to the shell,
                # which means the user's configured default application handles
                # the audio file. MasVis itself never becomes an audio player.
                os.startfile(str(path))
                return

            # Development fallback for non-Windows hosts. Production builds are
            # Windows-only, but keeping this branch makes source-level checks
            # graceful on other platforms.
            if QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(path))
            ):
                return

            raise OSError(
                "No default application accepted the file."
            )
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1155:
                QMessageBox.information(
                    self,
                    "No default audio player",
                    (
                        "Windows has no default app associated with this audio file type.\n\n"
                        "Choose a default audio player in Windows Settings, then try Play again."
                    ),
                )
                return

            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("Could not open audio file")
            box.setText(
                "The current audio file could not be opened in the system's default application."
            )
            box.setInformativeText(str(exc))
            box.exec()

    def current_export_view(self):
        widget = self.tabs.currentWidget()

        if isinstance(widget, (ReportView, OverviewView)):
            return widget

        return None

    # --------------------------------------------------------
    # Open / analysis
    # --------------------------------------------------------

    def open_files(self):
        start_directory = _existing_directory(
            self.preferences.get("open_directory")
        )
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Files",
            str(start_directory),
            AUDIO_FILTER,
        )

        if file_paths:
            self.preferences["open_directory"] = str(Path(file_paths[0]).parent)
            self.save_preferences()
            self.start_analysis(
                [Path(path) for path in file_paths]
            )

    def show_advanced_open(self):
        if (
            self.analysis_thread is not None
            and self.analysis_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "Processing",
                "An analysis is already running.",
            )
            return

        dialog = AdvancedOpenDialog(
            self.system_dark,
            initial_directory=self.preferences.get("open_directory"),
            parent=self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        config = dialog.configuration()
        self.preferences["open_directory"] = str(
            _existing_directory(config.get("last_directory"))
        )
        self.save_preferences()

        files = self.resolve_advanced_inputs(
            config["inputs"],
            config["recursive"],
        )

        if not files:
            QMessageBox.information(
                self,
                "Advanced Open",
                "No supported audio files were found.",
            )
            return

        self.start_analysis(
            files,
            r128_unit=config["r128_unit"],
            overview_mode=config["overview_mode"],
        )

    def resolve_advanced_inputs(self, inputs, recursive):
        resolved = []
        seen = set()

        def add_file(path):
            path = Path(path).absolute()
            key = str(path).casefold()

            if key in seen:
                return

            seen.add(key)
            resolved.append(path)

        for input_path in inputs:
            path = Path(input_path)

            if path.is_file():
                add_file(path)
                continue

            if not path.is_dir():
                continue

            try:
                if recursive:
                    candidates = sorted(
                        (p for p in path.rglob("*") if p.is_file()),
                        key=lambda p: str(p).casefold(),
                    )
                else:
                    candidates = sorted(
                        (p for p in path.iterdir() if p.is_file()),
                        key=lambda p: str(p).casefold(),
                    )
            except OSError:
                continue

            for candidate in candidates:
                if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                    add_file(candidate)

        return resolved

    def request_analysis_cancel(self):
        """Set the worker's thread-safe cancel flag immediately from the GUI."""
        worker = self.analysis_worker
        if worker is not None:
            # Deliberately use a direct Python call here.  Connecting the button
            # straight to a method on the moved worker QObject creates a queued
            # cross-thread call, but the worker thread is busy inside run() and
            # cannot service that queue until the batch is already finished.
            worker.request_cancel()

        if self.processing_dialog is not None:
            self.processing_dialog.request_cancel_visual()

    def start_analysis(
        self,
        paths,
        r128_unit="LUFS",
        overview_mode=None,
    ):
        if (
            self.analysis_thread is not None
            and self.analysis_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "Processing",
                "An analysis is already running.",
            )
            return

        valid_paths = []

        for path in paths:
            path = Path(path)

            if not path.is_file():
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                answer = QMessageBox.question(
                    self,
                    "Unknown file type",
                    (
                        f"{path.name}\n\n"
                        "This extension is not in the current "
                        "format list.\n\n"
                        "FFmpeg may still be able to decode it. "
                        "Try it anyway?"
                    ),
                )

                if (
                    answer
                    != QMessageBox.StandardButton.Yes
                ):
                    continue

            valid_paths.append(path)

        if not valid_paths:
            return

        self.close_after_cancel = False

        self.processing_dialog = ProcessingDialog(
            len(valid_paths),
            self,
        )

        self.analysis_thread = QThread(self)
        self.analysis_worker = AnalysisWorker(
            valid_paths,
            r128_unit=r128_unit,
            overview_mode=overview_mode,
            render_scale=self.report_render_scale(),
            report_font=self.preferences.get("report_font", ""),
            report_theme=self.preferences.get("report_theme", "Light"),
        )

        self.analysis_worker.moveToThread(
            self.analysis_thread
        )

        self.analysis_thread.started.connect(
            self.analysis_worker.run
        )

        self.analysis_worker.progress.connect(
            self.processing_dialog.progress.setValue
        )

        self.analysis_worker.status.connect(
            self.processing_dialog.status_label.setText
        )

        self.analysis_worker.file_started.connect(
            self.processing_dialog.set_current_file
        )

        self.analysis_worker.item_finished.connect(
            self.add_report
        )

        self.analysis_worker.overview_finished.connect(
            self.add_overview_tabs
        )

        self.analysis_worker.item_failed.connect(
            self.analysis_failed
        )

        self.analysis_worker.batch_finished.connect(
            self.analysis_finished
        )

        self.analysis_worker.batch_finished.connect(
            self.analysis_thread.quit
        )

        self.processing_dialog.cancel_button.clicked.connect(
            self.request_analysis_cancel
        )

        self.analysis_thread.finished.connect(
            self.analysis_worker.deleteLater
        )

        self.analysis_thread.finished.connect(
            self.thread_finished
        )

        self.open_button.setEnabled(False)
        self.advanced_button.setEnabled(False)

        self.processing_dialog.show()
        self.analysis_thread.start()

    def add_report(self, result):
        try:
            report = ReportView(
                result,
                self,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Display error",
                str(exc),
            )
            return

        index = self.tabs.addTab(
            report,
            result["path"].name,
        )

        self.tabs.setTabToolTip(
            index,
            str(result["path"]),
        )

        self.tabs.setCurrentIndex(index)

        self.empty_page.setVisible(False)
        self.tabs.setVisible(True)

        self.update_tab_bar()

        QTimer.singleShot(
            0,
            report.fit_to_window,
        )

        QTimer.singleShot(
            20,
            self.update_header_for_current_tab,
        )

    def add_overview_tabs(self, overview_tabs):
        last_index = -1

        for result in overview_tabs:
            try:
                view = OverviewView(
                    result,
                    self,
                )
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Display error",
                    str(exc),
                )
                continue

            index = self.tabs.addTab(
                view,
                result["label"],
            )
            self.tabs.setTabToolTip(
                index,
                result.get("tooltip", ""),
            )
            last_index = index

        if last_index >= 0:
            self.tabs.setCurrentIndex(last_index)
            self.empty_page.setVisible(False)
            self.tabs.setVisible(True)
            self.update_tab_bar()

            current_view = self.tabs.widget(last_index)
            if isinstance(current_view, OverviewView):
                QTimer.singleShot(
                    0,
                    current_view.fit_to_window,
                )

            QTimer.singleShot(
                20,
                self.update_header_for_current_tab,
            )

    def analysis_failed(
        self,
        file_path,
        message,
        details,
    ):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Analysis error")
        box.setText(Path(file_path).name)
        box.setInformativeText(
            message or "Unknown error."
        )

        if details:
            box.setDetailedText(details)

        box.exec()

    def analysis_finished(self, cancelled):
        if self.processing_dialog is not None:
            self.processing_dialog.close()
            self.processing_dialog = None

        self.open_button.setEnabled(True)
        self.advanced_button.setEnabled(True)

        if self.close_after_cancel:
            QTimer.singleShot(0, self.close)

    def thread_finished(self):
        self.analysis_thread = None
        self.analysis_worker = None

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)

        if widget is not None:
            widget.deleteLater()

        self.update_tab_bar()

        if self.tabs.count() == 0:
            self.tabs.setVisible(False)
            self.empty_page.setVisible(True)
            self.zoom_frame.setVisible(False)
            self.dr_button.setVisible(False)
            self.assessment_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.save_all_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.file_info_button.setEnabled(False)
            self.compare_button.setEnabled(False)
        else:
            self.update_header_for_current_tab()

    def update_tab_bar(self):
        count = self.tabs.count()

        # Windows UX decision: always show a result tab, even when
        # exactly one result is open, so its X can restore the empty
        # start screen without requiring another command.
        self.tabs.tabBar().setVisible(count > 0)
        self.tabs.setTabsClosable(count > 0)

        comparable_count = sum(
            1
            for index in range(count)
            if isinstance(
                self.tabs.widget(index),
                (ReportView, OverviewView),
            )
        )
        self.compare_button.setEnabled(
            comparable_count > 1
        )

    def on_tab_changed(self, index):
        self.update_header_for_current_tab()

    # --------------------------------------------------------
    # Header / DR / zoom
    # --------------------------------------------------------

    def update_header_for_current_tab(self):
        widget = self.tabs.currentWidget()

        self.save_all_button.setEnabled(self.tabs.count() > 0)

        if isinstance(widget, OverviewView):
            self.dr_button.setVisible(False)
            self.assessment_button.setEnabled(False)
            self.save_button.setEnabled(True)
            # An Overview can contain several files, so there is no single
            # unambiguous playback target for the Play action.
            self.play_button.setEnabled(False)
            self.file_info_button.setEnabled(False)

            self.zoom_indicator.setText(
                str(widget.current_width)
            )
            self.zoom_frame.adjustSize()
            self.zoom_frame.setVisible(True)
            self.position_zoom_overlay()
            return

        report = self.current_report()

        if report is None:
            self.dr_button.setVisible(False)
            self.assessment_button.setEnabled(False)
            self.zoom_frame.setVisible(False)
            self.save_button.setEnabled(False)
            self.play_button.setEnabled(False)
            self.file_info_button.setEnabled(False)
            return

        dr = report.result["dr"]
        dr_text = "??.?" if dr < 0 else f"{dr:.1f}"

        self.dr_button.setText(dr_text)

        color = dr_color(dr)
        text_color = (
            "#111111"
            if dr is not None and dr >= 10
            else "#ffffff"
        )

        self.dr_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: {text_color};
                font-family: Consolas, "Courier New", monospace;
                font-size: 16px;
                font-weight: 700;
                border: 2px solid #e8e8e8;
                border-radius: 7px;
                padding: 1px 4px;
            }}

            QPushButton:hover {{
                border-color: white;
            }}
            """
        )

        self.dr_button.setVisible(True)
        has_assessment = bool(
            report.result.get("dynamics_assessment")
        )
        self.assessment_button.setEnabled(has_assessment)
        self.save_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.file_info_button.setEnabled(True)

        self.zoom_indicator.setText(
            str(report.current_width)
        )

        self.zoom_frame.adjustSize()
        self.zoom_frame.setVisible(True)
        self.position_zoom_overlay()

    def position_zoom_overlay(self):
        if not self.zoom_frame.isVisible():
            return

        self.zoom_frame.adjustSize()

        width = self.zoom_frame.width()
        height = self.zoom_frame.height()

        x = max(
            8,
            (self.content_area.width() - width) // 2,
        )

        y = max(
            8,
            self.content_area.height()
            - height
            - 12,
        )

        self.zoom_frame.move(x, y)
        self.zoom_frame.raise_()

    def zoom_current(self, delta):
        view = self.current_export_view()

        if view is None:
            return

        view.zoom_by(delta)
        self.zoom_indicator.setText(
            str(view.current_width)
        )

    def zoom_original(self):
        view = self.current_export_view()

        if view is None:
            return

        view.original_size()
        self.zoom_indicator.setText(
            str(view.current_width)
        )

    def fit_current(self):
        view = self.current_export_view()

        if view is None:
            return

        view.fit_to_window()
        self.zoom_indicator.setText(
            str(view.current_width)
        )

    # --------------------------------------------------------
    # Compare
    # --------------------------------------------------------

    def comparable_tab_entries(self):
        entries = []

        for index in range(
            self.tabs.count()
        ):
            view = self.tabs.widget(
                index
            )

            if not isinstance(
                view,
                (ReportView, OverviewView),
            ):
                continue

            title = self.tabs.tabText(
                index
            )

            tooltip = (
                self.tabs.tabToolTip(
                    index
                )
            )

            if isinstance(
                view,
                ReportView,
            ):
                path = str(
                    view.result.get(
                        "path",
                        "",
                    )
                )

                subtitle = (
                    path
                    if path
                    else "Detailed report"
                )

                kind = "Detailed"

            else:
                source_paths = (
                    view.result.get(
                        "source_paths",
                        [],
                    )
                )

                if len(source_paths) == 1:
                    subtitle = str(
                        source_paths[0]
                    )
                else:
                    subtitle = (
                        "Overview - "
                        f"{len(source_paths)} files"
                    )

                kind = "Overview"

            entry = {
                "title": title,
                "subtitle": (
                    f"{kind} · {subtitle}"
                ),
                "tooltip": (
                    tooltip
                    or subtitle
                ),
                "png_data": bytes(
                    view.png_data
                ),
                "dynamics_capable": False,
            }

            if isinstance(view, ReportView):
                assessment_metrics = dict(
                    (view.result.get("dynamics_assessment") or {}).get("metrics") or {}
                )
                assessment_metrics.update({
                    "dr": view.result.get("dr"),
                    "dr_channels": view.result.get("dr_channels"),
                    "integrated_lufs": view.result.get("lufs"),
                    "lra_lu": view.result.get("lra"),
                    "plr_lu": view.result.get("plr"),
                    "crest_total_db": view.result.get("crest"),
                    "true_peak_dbtp": view.result.get("true_peak"),
                })
                entry.update({
                    "dynamics_capable": bool(path),
                    "path": path,
                    "dynamics_metrics": assessment_metrics,
                })

            entries.append(entry)

        return entries

    def show_compare(self):
        entries = (
            self.comparable_tab_entries()
        )

        if len(entries) < 2:
            QMessageBox.information(
                self,
                "Cannot Compare",
                (
                    "At least two result tabs "
                    "are required."
                ),
            )
            return

        gif_resolution = self.preferences.get("gif_resolution", "High")
        dialog = CompareSelectionDialog(
            entries,
            gif_duration_ms=(
                int(self.preferences.get("gif_duration", 3))
                * 1000
            ),
            gif_frame_width=GIF_RESOLUTION_WIDTHS.get(
                gif_resolution,
                810,
            ),
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        selected = (
            dialog.selected_entries
        )

        if len(selected) < 2:
            return

        if dialog.action_mode == "dynamics":
            self.start_dynamics_comparison(selected)
            return

        self.comparison_counter += 1

        window = ComparisonWindow(
            selected,
            self.comparison_counter,
            plot_width=int(
                self.preferences.get("comparison_width", 606)
            ),
            on_plot_width_changed=self.remember_comparison_width,
            parent=None,
        )

        self.comparison_windows.append(
            window
        )

        window.destroyed.connect(
            lambda _obj=None, w=window:
            self.release_comparison_window(w)
        )

        window.show()
        window.raise_()
        window.activateWindow()

    def remember_comparison_width(self, width):
        width = max(
            COMPARISON_MIN_PLOT_WIDTH,
            min(int(width), 1080),
        )
        self.preferences["comparison_width"] = width
        self.save_preferences()

    def release_comparison_window(
        self,
        window,
    ):
        try:
            self.comparison_windows.remove(
                window
            )
        except ValueError:
            pass

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    def save_current(self):
        view = self.current_export_view()

        if view is None:
            return

        default_format = self.preferences.get("save_format", "PNG")
        if default_format not in SAVE_FORMATS:
            default_format = "PNG"

        info = SAVE_FORMATS[default_format]

        if isinstance(view, ReportView):
            base_name = view.result.get(
                "default_save_name",
                view.result["path"].stem + " - MasVis.png",
            )
        else:
            base_name = view.result.get(
                "default_save_name",
                "Overview - MasVis.png",
            )

        default_directory = _existing_directory(
            self.preferences.get("save_directory")
        )
        default_path = (
            default_directory
            / (Path(base_name).stem + info["extension"])
        )

        dialog, quality_combo = _report_save_dialog(
            self,
            "Save Current Tab",
            default_path,
            default_format,
            self.preferences.get("export_resolution", "High"),
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_files = dialog.selectedFiles()
        if not selected_files:
            return

        output_path = selected_files[0]
        save_format = image_format_from_path(
            output_path,
            dialog.selectedNameFilter(),
            default_format,
        )
        export_resolution = quality_combo.currentData() or "High"
        self.preferences["save_directory"] = str(Path(output_path).parent)

        # Keep the last choices as convenience defaults without exposing them
        # as global Preferences; every save can still choose them explicitly.
        self.preferences["save_format"] = save_format
        self.preferences["export_resolution"] = export_resolution
        self.save_preferences()

        try:
            save_report_image(
                view.png_data,
                output_path,
                save_format=save_format,
                export_resolution=export_resolution,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save error",
                str(exc),
            )

    def save_all(self):
        if self.tabs.count() == 0:
            return

        default_directory = _existing_directory(
            self.preferences.get("save_directory")
        )

        default_format = self.preferences.get("save_format", "PNG")
        default_quality = self.preferences.get("export_resolution", "High")

        dialog, format_combo, quality_combo = _report_save_all_dialog(
            self,
            default_directory,
            default_format,
            default_quality,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dialog.selectedFiles()
        if not selected:
            return

        directory = Path(selected[0])
        self.preferences["save_directory"] = str(directory)
        save_format = format_combo.currentText()
        if save_format not in SAVE_FORMATS:
            save_format = "PNG"
        export_resolution = quality_combo.currentData() or "High"
        extension = SAVE_FORMATS[save_format]["extension"]

        self.preferences["save_format"] = save_format
        self.preferences["export_resolution"] = export_resolution
        self.save_preferences()

        try:
            for index in range(self.tabs.count()):
                view = self.tabs.widget(index)

                if not isinstance(
                    view,
                    (ReportView, OverviewView),
                ):
                    continue

                if isinstance(view, ReportView):
                    base_name = view.result.get(
                        "default_save_name",
                        view.result["path"].stem + " - MasVis.png",
                    )
                else:
                    base_name = view.result.get(
                        "default_save_name",
                        "Overview - MasVis.png",
                    )

                output_path = (
                    directory
                    / (Path(base_name).stem + extension)
                )

                if output_path.exists():
                    number = 2

                    while True:
                        candidate = (
                            directory
                            / (
                                output_path.stem
                                + f" ({number})"
                                + output_path.suffix
                            )
                        )

                        if not candidate.exists():
                            output_path = candidate
                            break

                        number += 1

                save_report_image(
                    view.png_data,
                    output_path,
                    save_format=save_format,
                    export_resolution=export_resolution,
                )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save All error",
                str(exc),
            )
            return

    # --------------------------------------------------------
    # Dynamics Comparison
    # --------------------------------------------------------

    def start_dynamics_comparison(self, entries):
        if len(entries) != 2 or not all(entry.get("dynamics_capable") for entry in entries):
            QMessageBox.information(
                self,
                "Cannot Compare Dynamics",
                "Select exactly two detailed report tabs.",
            )
            return

        if (
            self.analysis_thread is not None
            and self.analysis_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "Processing",
                "Wait for the current audio analysis to finish first.",
            )
            return

        if (
            self.dynamics_compare_thread is not None
            and self.dynamics_compare_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "Dynamics Comparison",
                "A Dynamics Comparison is already running.",
            )
            return


        for entry in entries:
            path = Path(entry.get("path", ""))
            if not path.is_file():
                QMessageBox.warning(
                    self,
                    "Dynamics Comparison",
                    f"The original audio file could not be found:\n\n{path}",
                )
                return

        entry_a, entry_b = entries
        self.dynamics_compare_progress = DynamicsComparisonProgressDialog(
            entry_a, entry_b, self
        )
        self.dynamics_compare_thread = QThread(self)
        self.dynamics_compare_worker = DynamicsComparisonWorker(entry_a, entry_b)
        self.dynamics_compare_worker.moveToThread(self.dynamics_compare_thread)

        self.dynamics_compare_thread.started.connect(
            self.dynamics_compare_worker.run
        )
        self.dynamics_compare_worker.status.connect(
            self.dynamics_compare_progress.status_label.setText
        )
        self.dynamics_compare_worker.finished.connect(
            self.dynamics_comparison_finished
        )
        self.dynamics_compare_worker.failed.connect(
            self.dynamics_comparison_failed
        )
        self.dynamics_compare_worker.finished.connect(
            self.dynamics_compare_thread.quit
        )
        self.dynamics_compare_worker.failed.connect(
            self.dynamics_compare_thread.quit
        )
        self.dynamics_compare_thread.finished.connect(
            self.dynamics_compare_worker.deleteLater
        )
        self.dynamics_compare_thread.finished.connect(
            self.dynamics_compare_thread_finished
        )

        self.dynamics_compare_progress.show()
        self.dynamics_compare_thread.start()

    def dynamics_comparison_finished(self, result):
        if self.dynamics_compare_progress is not None:
            self.dynamics_compare_progress.close()

        dialog = DynamicsComparisonDialog(
            result,
            dark=self.system_dark,
            parent=self,
        )
        dialog.exec()

    def dynamics_comparison_failed(self, message, details):
        if self.dynamics_compare_progress is not None:
            self.dynamics_compare_progress.close()

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Dynamics Comparison failed")
        box.setText(message or "The two files could not be compared.")
        box.setDetailedText(details or "")
        box.exec()

    def dynamics_compare_thread_finished(self):
        if self.dynamics_compare_progress is not None:
            self.dynamics_compare_progress.deleteLater()
        self.dynamics_compare_progress = None
        self.dynamics_compare_worker = None
        self.dynamics_compare_thread = None

    # --------------------------------------------------------
    # DR
    # --------------------------------------------------------

    def show_dr_details(self):
        report = self.current_report()

        if report is None:
            return

        dialog = DRDetailsDialog(
            report,
            self.show_dr_chart,
            self,
        )
        dialog.exec()

    def show_dr_chart(self):
        if not DR_CHART_SVG.is_file():
            QMessageBox.warning(
                self,
                "Dynamic Range Chart",
                "The upstream Dynamic Range Chart could not be found.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Dynamic Range Chart")
        dialog.setWindowFlag(
            Qt.WindowType.WindowContextHelpButtonHint,
            False,
        )
        dialog.setFixedSize(340, 550)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(8, 8, 8, 8)

        svg = QSvgWidget(str(DR_CHART_SVG))
        svg.setObjectName("drChart")

        layout.addWidget(svg)
        dialog.exec()

    # --------------------------------------------------------
    # Dynamics Assessment
    # --------------------------------------------------------

    def show_dynamics_assessment(self):
        report = self.current_report()

        if report is None:
            return

        if not report.result.get("dynamics_assessment"):
            QMessageBox.information(
                self,
                "Dynamics Assessment",
                "No Dynamics Assessment is available for this result.",
            )
            return

        dialog = DynamicsAssessmentDialog(
            report,
            self,
        )
        dialog.exec()

    # --------------------------------------------------------
    # File information
    # --------------------------------------------------------

    def show_file_information(self):
        report = self.current_report()

        if report is None:
            return

        dialog = FileInformationDialog(
            report,
            self,
        )
        dialog.exec()

    # --------------------------------------------------------
    # Help / misc
    # --------------------------------------------------------

    def show_shortcuts(self):
        dialog = KeyboardShortcutsDialog(
            self
        )
        dialog.exec()

    def show_help(self, page="Getting Started"):
        dialog = HelpDialog(
            self,
            initial_page=page,
        )
        dialog.exec()

    def show_about(self):
        dialog = AboutDialog(
            self
        )
        dialog.exec()

    def not_ported(self, feature):
        QMessageBox.information(
            self,
            feature,
            (
                f"{feature} exists in MasVisGtk and is retained "
                "for feature parity.\n\n"
                "Its Windows implementation has deliberately "
                "not been ported yet."
            ),
        )

    # --------------------------------------------------------
    # Drag & drop
    # --------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()

        if any(url.isLocalFile() for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile()
        ]

        file_paths = [
            path
            for path in paths
            if path.is_file()
        ]

        if file_paths:
            self.start_analysis(file_paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    # --------------------------------------------------------
    # Window events
    # --------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_zoom_overlay()

    def closeEvent(self, event):
        if (
            self.dynamics_compare_thread is not None
            and self.dynamics_compare_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "Dynamics Comparison",
                "A Dynamics Comparison is still running. Wait for it to finish before closing the application.",
            )
            event.ignore()
            return

        if (
            self.analysis_thread is not None
            and self.analysis_thread.isRunning()
        ):
            answer = QMessageBox.question(
                self,
                "Processing",
                (
                    "Audio processing is still running.\n\n"
                    "Request cancellation and close when the "
                    "current calculation has finished?"
                ),
            )

            if (
                answer
                == QMessageBox.StandardButton.Yes
            ):
                self.close_after_cancel = True
                self.analysis_worker.request_cancel()

                if self.processing_dialog is not None:
                    self.processing_dialog.request_cancel_visual()

            event.ignore()
            return

        event.accept()


# ============================================================
# Application identity / settings compatibility
# ============================================================


def set_windows_app_user_model_id():
    """Give Windows a stable identity for taskbar/grouping and packaged builds."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID
        )
    except Exception:
        # Cosmetic shell integration must never prevent the app from starting.
        pass


def migrate_legacy_settings():
    """Copy prototype preferences once after the public product rename."""
    current = QSettings()
    if current.allKeys():
        return

    legacy = QSettings(
        LEGACY_SETTINGS_ORGANIZATION,
        LEGACY_SETTINGS_APPLICATION,
    )
    legacy_keys = legacy.allKeys()
    if not legacy_keys:
        return

    for key in legacy_keys:
        current.setValue(key, legacy.value(key))
    current.sync()


# ============================================================
# Entry point
# ============================================================


def main():
    set_windows_app_user_model_id()

    app = QApplication(sys.argv)

    app.setOrganizationName(SETTINGS_ORGANIZATION)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    migrate_legacy_settings()

    if APP_ICON.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
