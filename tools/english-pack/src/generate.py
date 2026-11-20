"""把课程 JSON 灌进可复用练习页模板，写出独立练习页。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .course import CourseError, load_course

SRC_DIR = Path(__file__).resolve().parent
TEMPLATE = SRC_DIR / "_practice_template.html"
CSS = SRC_DIR / "_practice.css"
JS = SRC_DIR / "_practice.js"


def _escape_script(text: str) -> str:
    return text.replace("</script", "<\\/script")


def render_practice(course: dict[str, Any]) -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    payload = json.dumps(course, ensure_ascii=False, indent=2)
    title = f"{course['title']} · 跟读练习"
    html = html.replace("__PAGE_TITLE__", title)
    html = html.replace("__PRACTICE_CSS__", css)
    html = html.replace("__COURSE_JSON__", _escape_script(payload))
    html = html.replace("__PRACTICE_JS__", js)
    return html


def _copy_audio_files(course: dict[str, Any], source_root: Path, dest_dir: Path) -> None:
    for sentence in course["sentences"]:
        rel = sentence.get("audio") or ""
        if not rel:
            continue
        src = (source_root / rel).resolve()
        dest = (dest_dir / rel).resolve()
        if not str(src).startswith(str(source_root.resolve())):
            raise CourseError(f"音频路径超出课程目录：{rel}")
        if not str(dest).startswith(str(dest_dir.resolve())):
            raise CourseError(f"音频输出路径不合法：{rel}")
        if not src.is_file():
            raise CourseError(f"找不到本地音频：{src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def write_practice(course_path: Path, dest_dir: Path) -> Path:
    course = load_course(course_path)
    dest_dir = dest_dir.expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    html_path = dest_dir / "index.html"
    html_path.write_text(render_practice(course), encoding="utf-8")
    _copy_audio_files(course, course_path.expanduser().resolve().parent, dest_dir)
    meta = {
        "tool": "english-pack",
        "course_id": course["id"],
        "title": course["title"],
        "sentences": len(course["sentences"]),
        "source": str(course_path.expanduser().resolve()),
    }
    (dest_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return html_path
