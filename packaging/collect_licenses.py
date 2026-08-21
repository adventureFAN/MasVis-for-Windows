# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 adventureFAN
"""Collect license/notice files and license metadata from the exact Python build environment."""

from __future__ import annotations

import importlib.metadata as metadata
import shutil
import sys
from pathlib import Path


DISTRIBUTIONS = [
    "contourpy",
    "cycler",
    "fonttools",
    "kiwisolver",
    "matplotlib",
    "numpy",
    "packaging",
    "pillow",
    "pyparsing",
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "python-dateutil",
    "scipy",
    "shiboken6",
    "six",
    "PyInstaller",
]

QT_DISTRIBUTIONS = {
    "PySide6",
    "PySide6_Addons",
    "PySide6_Essentials",
    "shiboken6",
}

LICENSE_PREFIXES = ("license", "copying", "notice", "copyright")


def is_license_path(path: Path) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    return "licenses" in lower_parts or name.startswith(LICENSE_PREFIXES)


def safe_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


def metadata_value(dist: metadata.Distribution, key: str) -> str:
    value = dist.metadata.get(key)
    return value.strip() if value else ""


def write_distribution_metadata(dist: metadata.Distribution, target: Path) -> tuple[str, str]:
    name = metadata_value(dist, "Name") or "Unknown"
    version = dist.version
    license_expression = metadata_value(dist, "License-Expression")
    legacy_license = metadata_value(dist, "License")
    home_page = metadata_value(dist, "Home-page")
    project_urls = dist.metadata.get_all("Project-URL") or []

    lines = [
        f"Name: {name}",
        f"Version: {version}",
        f"License-Expression: {license_expression or '(not provided)'}",
        f"Legacy-License: {legacy_license or '(not provided)'}",
        f"Home-page: {home_page or '(not provided)'}",
    ]
    if project_urls:
        lines.append("Project-URL:")
        lines.extend(f"  {value}" for value in project_urls)

    target.mkdir(parents=True, exist_ok=True)
    (target / "PACKAGE-METADATA.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return license_expression, legacy_license


def copy_distribution(name: str, output: Path) -> tuple[str, str, int, str, str]:
    dist = metadata.distribution(name)
    version = dist.version
    canonical_name = dist.metadata["Name"] or name
    target = output / f"{safe_component(canonical_name)}-{safe_component(version)}"
    count = 0

    for entry in dist.files or []:
        rel = Path(str(entry))
        if not is_license_path(rel):
            continue
        source = Path(dist.locate_file(entry))
        if not source.is_file():
            continue
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1

    license_expression, legacy_license = write_distribution_metadata(dist, target)
    return name, version, count, license_expression, legacy_license


def copy_python_license(output: Path) -> int:
    candidates = [
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.base_prefix) / "LICENSE",
        Path(sys.prefix) / "LICENSE.txt",
        Path(sys.prefix) / "LICENSE",
    ]
    for source in candidates:
        if source.is_file():
            target = output / f"Python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target / source.name)
            return 1
    return 0


def copy_common_release_material(project_root: Path, output: Path) -> int:
    source_dir = project_root / "packaging" / "licenses"
    target_dir = output / "_COMMON-LICENSES"
    count = 0
    if source_dir.is_dir():
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in sorted(source_dir.iterdir()):
            if not source.is_file():
                continue
            shutil.copy2(source, target_dir / source.name)
            count += 1

    source_access = project_root / "packaging" / "THIRD_PARTY_SOURCE.md"
    if source_access.is_file():
        target = output / "_SOURCE-ACCESS"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_access, target / source_access.name)
        count += 1
    return count


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    output = project_root / "release-license-staging"
    if len(sys.argv) > 1:
        output = Path(sys.argv[1]).resolve()

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    qt_open_source_metadata: list[str] = []

    print(f"License output: {output}")
    for name in DISTRIBUTIONS:
        try:
            dist_name, version, count, license_expression, legacy_license = copy_distribution(name, output)
        except metadata.PackageNotFoundError:
            print(f"MISSING PACKAGE: {name}")
            missing.append(name)
            continue

        print(f"{dist_name} {version}: {count} license/notice file(s) + package metadata")
        if count == 0:
            missing.append(f"{dist_name} (no package license/notice file found)")

        if name in QT_DISTRIBUTIONS:
            combined = f"{license_expression} {legacy_license}".upper()
            if "GPL" in combined or "LGPL" in combined:
                qt_open_source_metadata.append(f"{dist_name} {version}: {license_expression or legacy_license}")
            else:
                missing.append(f"{dist_name} (open-source GPL/LGPL license metadata not found)")

    python_count = copy_python_license(output)
    print(f"Python {sys.version.split()[0]}: {python_count} license file(s)")
    if python_count == 0:
        missing.append("Python runtime license")

    common_count = copy_common_release_material(project_root, output)
    print(f"Common/source-access release material: {common_count} file(s)")
    if common_count < 4:
        missing.append("common GPL/LGPL/Apache license texts and/or source-access note")

    if qt_open_source_metadata:
        print("\nQt for Python open-source license metadata:")
        for item in qt_open_source_metadata:
            print(f"  - {item}")

    if missing:
        print("\nREVIEW REQUIRED:")
        for item in missing:
            print(f"  - {item}")
        return 2

    print("\nPython/runtime license discovery completed without missing requested inputs.")
    print("NOTE: this does not close the separate FFmpeg corresponding-source/manual runtime legal review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
