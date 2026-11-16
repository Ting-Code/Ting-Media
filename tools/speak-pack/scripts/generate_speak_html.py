#!/usr/bin/env python3
"""Generate a 9:16 speaking / shadowing rec-screen HTML page."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from html import escape
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from episode_path import episode_dir  # noqa: E402

TEMPLATE = SRC / "_speak_template.html"
NAV = SRC / "_speak_nav.js"


def _parse_day(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _load_payload(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("JSON 根节点必须是对象")
    slides = data.get("slides")
    if not isinstance(slides, list) or not slides:
        raise SystemExit("JSON 需要非空的 slides 列表")
    clean = []
    for i, raw in enumerate(slides, 1):
        if not isinstance(raw, dict):
            raise SystemExit(f"第 {i} 页不是对象")
        words = []
        for w in raw.get("words") or []:
            if isinstance(w, str):
                words.append({"text": w, "meaning": ""})
            elif isinstance(w, dict) and str(w.get("text") or "").strip():
                words.append({
                    "text": str(w.get("text") or "").strip(),
                    "meaning": str(w.get("meaning") or "").strip(),
                })
        clean.append({
            "title": str(raw.get("title") or f"第 {i} 页").strip(),
            "tag": str(raw.get("tag") or raw.get("title") or f"第 {i} 页").strip(),
            "script": str(raw.get("script") or "").rstrip(),
            "en": str(raw.get("en") or "").strip(),
            "zh": str(raw.get("zh") or "").strip(),
            "attr": str(raw.get("attr") or "").strip(),
            "words": words,
        })
    data["slides"] = clean
    return data


def render(payload: dict, *, theme: str, day: date, title: str, subtitle: str) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    nav = NAV.read_text(encoding="utf-8")
    slides_json = json.dumps(payload["slides"], ensure_ascii=False, indent=2)
    # Place JSON inside a script tag; escape only the closing sequence.
    slides_json = slides_json.replace('<' + '/script', '<' + '\\/script')
    html = html.replace("__TITLE__", escape(title))
    html = html.replace("__SUBTITLE__", escape(subtitle))
    html = html.replace("__DATE__", escape(day.isoformat()))
    html = html.replace("__SLIDES_JSON__", slides_json)
    html = html.replace("__SPEAK_NAV__", nav)
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="生成口播 / 跟读 9:16 录屏页")
    parser.add_argument("json", type=Path, help="口播稿 JSON")
    parser.add_argument("--theme", help="期次主题，默认用 JSON 里的 theme 或 title")
    parser.add_argument("--date", help="YYYY-MM-DD，默认用 JSON 或今天")
    parser.add_argument("--niche", help="赛道目录，默认 english")
    parser.add_argument("--title", help="覆盖标题")
    parser.add_argument("--subtitle", help="覆盖副标题")
    parser.add_argument("--media-root", type=Path, help="Ting-Media 根目录，默认自动检测")
    args = parser.parse_args()

    src = args.json.expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"找不到稿件：{src}")

    payload = _load_payload(src)
    day = _parse_day(args.date or payload.get("date") or None)
    theme = (args.theme or payload.get("theme") or payload.get("title") or "口播").strip()
    niche = (args.niche or payload.get("niche") or "english").strip() or "english"
    title = (args.title or payload.get("title") or theme).strip()
    subtitle = (args.subtitle or payload.get("subtitle") or "每天一句，整句跟读").strip()

    out_dir = episode_dir(niche=niche, theme=theme, day=day, media_root=args.media_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "index.html"
    html_path.write_text(
        render(payload, theme=theme, day=day, title=title, subtitle=subtitle),
        encoding="utf-8",
    )
    meta = {
        "tool": "speak-pack",
        "theme": theme,
        "date": day.isoformat(),
        "niche": niche,
        "title": title,
        "subtitle": subtitle,
        "source": str(src),
        "pages": len(payload["slides"]),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(html_path)


if __name__ == "__main__":
    main()
