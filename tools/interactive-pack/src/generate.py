# -*- coding: utf-8 -*-
"""Generate offline interactive HTML packs from structured content."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .specs import get_spec

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def _escape_html(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    title = str(data.get("title") or "互动页").strip()
    subtitle = str(data.get("subtitle") or "").strip()
    brand = str(data.get("brand") or "Ting Media").strip()
    sections = data.get("sections") or []
    if not isinstance(sections, list):
        raise ValueError("sections must be a list")
    norm_sections = []
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            raise ValueError(f"sections[{i}] must be object")
        items = sec.get("items") or []
        if isinstance(items, list) and items and isinstance(items[0], str):
            items = [{"text": t} for t in items]
        norm_sections.append(
            {
                "heading": str(sec.get("heading") or f"板块 {i+1}"),
                "body": str(sec.get("body") or ""),
                "items": [
                    {
                        "title": str(it.get("title") or it.get("text") or ""),
                        "meta": str(it.get("meta") or ""),
                        "text": str(it.get("text") or ""),
                    }
                    for it in items
                    if isinstance(it, dict)
                ],
            }
        )
    return {
        "title": title,
        "subtitle": subtitle,
        "brand": brand,
        "date": str(data.get("date") or datetime.now().strftime("%Y-%m-%d")),
        "sections": norm_sections,
        "cta": str(data.get("cta") or "左右滑看下一页 · 点卡片展开"),
        "extra": data.get("extra") if isinstance(data.get("extra"), dict) else {},
    }


def _write_multifile(out: Path, payload: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    css = (TEMPLATES / "card.css").read_text(encoding="utf-8")
    js = (TEMPLATES / "card.js").read_text(encoding="utf-8")
    html = (TEMPLATES / "card.index.html").read_text(encoding="utf-8")
    html = (
        html.replace("{{TITLE}}", _escape_html(payload["title"]))
        .replace("{{BRAND}}", _escape_html(payload["brand"]))
        .replace("{{SUBTITLE}}", _escape_html(payload["subtitle"]))
        .replace("{{CTA}}", _escape_html(payload["cta"]))
        .replace("{{DATE}}", _escape_html(payload["date"]))
    )
    (out / "style.css").write_text(css, encoding="utf-8")
    boot = "window.__PACK_DATA__ = " + json.dumps(payload, ensure_ascii=False) + ";\n" + js
    (out / "app.js").write_text(boot, encoding="utf-8")
    (out / "index.html").write_text(html, encoding="utf-8")


def _write_single_html(out: Path, payload: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    css = (TEMPLATES / "card.css").read_text(encoding="utf-8")
    js = (TEMPLATES / "card.js").read_text(encoding="utf-8")
    boot = "window.__PACK_DATA__ = " + json.dumps(payload, ensure_ascii=False) + ";\n" + js
    title = _escape_html(payload["title"])
    brand = _escape_html(payload["brand"])
    subtitle = _escape_html(payload["subtitle"])
    cta = _escape_html(payload["cta"])
    date = _escape_html(payload["date"])
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="UTF-8"/>',
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>',
        f"<title>{title}</title>",
        "<style>",
        css,
        "</style>",
        "</head>",
        "<body>",
        '<header class="top">',
        f'  <div class="brand">{brand}</div>',
        f'  <h1 id="title">{title}</h1>',
        f'  <p class="sub" id="subtitle">{subtitle}</p>',
        f'  <p class="cta">{cta}</p>',
        f'  <p class="date">{date}</p>',
        "</header>",
        '<main id="app" class="deck" aria-live="polite"></main>',
        '<nav class="dots" id="dots" aria-label="页码"></nav>',
        "<script>",
        boot,
        "</script>",
        "</body>",
        "</html>",
        "",
    ]
    (out / "index.html").write_text("\n".join(parts), encoding="utf-8")


def generate(
    data: dict[str, Any],
    out_dir: Path,
    platform: str = "common",
    *,
    single_file: bool | None = None,
) -> Path:
    payload = normalize_payload(data)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if platform == "common":
        allow_inline = False
    else:
        spec = get_spec(platform)
        allow_inline = bool(spec.get("allow_inline_script", True))

    if single_file is None:
        single_file = False

    if single_file and not allow_inline and platform != "common":
        raise ValueError(f"{platform} 不允许内联脚本，不能生成单文件 HTML")
    if single_file and platform in ("xhs", "common"):
        raise ValueError("common/xhs 必须多文件外置 JS")

    if single_file:
        _write_single_html(out_dir, payload)
    else:
        _write_multifile(out_dir, payload)

    meta = {
        "platform": platform,
        "single_file": bool(single_file),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": payload["title"],
    }
    (out_dir / "pack.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_dir


def load_content_file(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
