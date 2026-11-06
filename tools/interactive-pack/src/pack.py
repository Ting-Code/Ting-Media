# -*- coding: utf-8 -*-
"""Zip offline packs with platform-aware checks."""
from __future__ import annotations

import zipfile
from pathlib import Path

from .validate import format_report, validate_dir


def build_zip(
    src_dir: Path,
    zip_path: Path,
    platform: str = "common",
    *,
    strict: bool = True,
) -> Path:
    src_dir = Path(src_dir).resolve()
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    report = validate_dir(src_dir, platform=platform)
    if strict and not report.ok:
        raise SystemExit("校验失败，拒绝打包：\n" + format_report(report))

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "pack.meta.json":
                continue
            arc = path.relative_to(src_dir).as_posix()
            zf.write(path, arcname=arc)
    return zip_path
