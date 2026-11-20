#!/usr/bin/env python3
"""Generate a self-contained English shadowing practice page."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT))

from src.course import CourseError  # noqa: E402
from src.generate import write_practice  # noqa: E402


def default_dest(course_id: str) -> Path:
    return ROOT / "practice" / course_id


def main() -> None:
    parser = argparse.ArgumentParser(description="生成英语跟读练习页（自用，不是录屏成片）")
    parser.add_argument(
        "json",
        nargs="?",
        type=Path,
        default=ROOT / "courses" / "frontend-workplace.json",
        help="课程 JSON，默认第一课 frontend-workplace",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="输出目录，默认 tools/english-pack/practice/<课程id>/",
    )
    args = parser.parse_args()

    src = args.json.expanduser().resolve()
    try:
        # 先读出 id 以决定默认目录；write_practice 会再校验一次。
        from src.course import load_course

        course = load_course(src)
        dest = (args.out or default_dest(course["id"])).expanduser().resolve()
        html_path = write_practice(src, dest)
    except CourseError as err:
        raise SystemExit(str(err)) from err

    print(html_path)


if __name__ == "__main__":
    main()
