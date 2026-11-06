# -*- coding: utf-8 -*-
"""Validate offline interactive packages against platform specs."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .specs import common_constraints, get_spec

NET_PATTERNS = [
    re.compile(r"""\bfetch\s*\(""", re.I),
    re.compile(r"""\bXMLHttpRequest\b"""),
    re.compile(r"""\bWebSocket\b"""),
    re.compile(r"""navigator\.sendBeacon\b"""),
]
CDN_URL = re.compile(r"""https?://""", re.I)
INLINE_SCRIPT = re.compile(r"""<script(?![^>]*\bsrc=)[^>]*>""", re.I)
EVENT_HANDLER = re.compile(r"""\son\w+\s*=""", re.I)
EVAL_PAT = re.compile(r"""\beval\s*\(|\bnew\s+Function\b|\.wasm\b""", re.I)
IFRAME_PAT = re.compile(r"""<iframe\b""", re.I)
ABS_ROOT = re.compile(r"""(?:src|href)\s*=\s*["']/[^"']+""", re.I)


@dataclass
class Finding:
    level: str  # error | warn
    code: str
    message: str
    path: str = ""


@dataclass
class Report:
    platform: str
    ok: bool
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, code: str, message: str, path: str = "") -> None:
        self.findings.append(Finding(level, code, message, path))
        if level == "error":
            self.ok = False


def _iter_text_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".html", ".htm", ".js", ".css", ".json", ".svg", ".txt", ".md"}:
            yield p


def _size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def validate_dir(root: Path, platform: str = "common") -> Report:
    root = root.resolve()
    if platform == "common":
        spec = {"id": "common", **common_constraints()}
    else:
        spec = get_spec(platform)

    report = Report(platform=spec["id"], ok=True)
    entry_name = spec.get("entry") or "index.html"
    entry = root / entry_name
    if not entry.is_file():
        # also accept nested single folder
        nested = [p for p in root.glob("*/index.html") if p.is_file()]
        if len(nested) == 1:
            root = nested[0].parent
            entry = nested[0]
        else:
            report.add("error", "missing_entry", f"缺少入口文件 {entry_name}", str(root))
            return report

    # zip-equivalent total size
    total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    total_mb = total / (1024 * 1024)
    zip_max = spec.get("zip_max_mb")
    if zip_max is not None and total_mb > float(zip_max):
        report.add("error", "zip_too_large", f"打包体积约 {total_mb:.2f}MB，超过上限 {zip_max}MB", str(root))

    entry_max = spec.get("entry_html_max_mb")
    if entry_max is not None and _size_mb(entry) > float(entry_max):
        report.add(
            "error",
            "entry_too_large",
            f"{entry.name} 为 {_size_mb(entry):.3f}MB，超过上限 {entry_max}MB",
            str(entry),
        )

    warn_any = spec.get("any_html_warn_mb")
    allow_inline = bool(spec.get("allow_inline_script", True))
    allow_handlers = bool(spec.get("allow_inline_event_handlers", allow_inline))
    allow_eval = bool(spec.get("allow_eval", False))
    allow_iframe = bool(spec.get("allow_iframe", False))
    allow_net = bool(spec.get("allow_network", False))
    allow_cdn = bool(spec.get("allow_external_cdn", False))

    for path in _iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(root))

        if path.suffix.lower() in {".html", ".htm"} and warn_any and _size_mb(path) > float(warn_any):
            report.add("warn", "html_large", f"HTML {rel} 约 {_size_mb(path):.1f}MB，偏大", rel)

        if not allow_cdn and CDN_URL.search(text):
            # allow data: and relative; flag http(s)
            report.add("error", "external_url", f"发现 http(s) 外链，离线包禁止 CDN/外网资源", rel)

        if not allow_net:
            for pat in NET_PATTERNS:
                if pat.search(text):
                    report.add("error", "network_api", f"发现网络 API：{pat.pattern}", rel)
                    break

        if path.suffix.lower() in {".html", ".htm", ".js"}:
            if not allow_eval and EVAL_PAT.search(text):
                report.add("error", "eval_forbidden", "禁止 eval / new Function / wasm", rel)
            if not allow_iframe and IFRAME_PAT.search(text):
                report.add("error", "iframe_forbidden", "禁止 iframe", rel)

        if path.suffix.lower() in {".html", ".htm"}:
            if not allow_inline and INLINE_SCRIPT.search(text):
                report.add("error", "inline_script", "该平台要求脚本外置，禁止内联 <script>", rel)
            if not allow_handlers and EVENT_HANDLER.search(text):
                report.add("error", "inline_handler", "禁止内联事件属性（如 onclick=）", rel)
            if ABS_ROOT.search(text):
                report.add("warn", "abs_root_path", "检测到以 / 开头的绝对路径，子路径托管下可能失效", rel)

    return report


def format_report(report: Report) -> str:
    lines = [f"platform={report.platform} ok={report.ok}"]
    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines)
    for f in report.findings:
        loc = f" @ {f.path}" if f.path else ""
        lines.append(f"  [{f.level}] {f.code}: {f.message}{loc}")
    return "\n".join(lines)
