#!/usr/bin/env python3
"""校验练习页生成结果。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.course import CourseError  # noqa: E402
from src.generate import write_practice  # noqa: E402

COURSE = ROOT / "courses" / "frontend-workplace.json"


class GenerateTests(unittest.TestCase):
    def test_writes_self_contained_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "practice"
            html_path = write_practice(COURSE, dest)
            self.assertTrue(html_path.is_file())
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("前端与职场常用句", html)
            self.assertIn("I'll take a look and get back to you.", html)
            self.assertIn("get back to you", html)
            self.assertIn("speechSynthesis", html)
            self.assertIn(".app {", html)
            self.assertIn("window.__ENGLISH_PACK_COURSE__", html)
            self.assertTrue((dest / "meta.json").is_file())
            # 单页自包含，不依赖外部 css/js 路径
            self.assertNotIn('href="_practice.css"', html)
            self.assertNotIn('src="_practice.js"', html)

    def test_missing_course_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "practice"
            with self.assertRaises(CourseError):
                write_practice(Path(tmp) / "missing.json", dest)


if __name__ == "__main__":
    unittest.main()
