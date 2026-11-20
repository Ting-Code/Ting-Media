#!/usr/bin/env python3
"""校验课程 JSON 与词条是否出现在原句中。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.course import CourseError, load_course, normalize_course  # noqa: E402

COURSE = ROOT / "courses" / "frontend-workplace.json"


class CourseTests(unittest.TestCase):
    def test_first_course_is_valid(self) -> None:
        course = load_course(COURSE)
        self.assertEqual(course["id"], "frontend-workplace")
        self.assertEqual(course["title"], "前端与职场常用句")
        count = len(course["sentences"])
        self.assertGreaterEqual(count, 10)
        self.assertLessEqual(count, 12)
        for sentence in course["sentences"]:
            self.assertTrue(sentence["en"])
            self.assertTrue(sentence["zh"])
            self.assertTrue(sentence["words"])

    def test_rejects_vocab_not_in_sentence(self) -> None:
        with self.assertRaises(CourseError):
            normalize_course({
                "id": "demo",
                "title": "示例",
                "sentences": [
                    {
                        "id": "s-1",
                        "en": "I'll follow up later.",
                        "zh": "我稍后再跟进。",
                        "words": [{"text": "ship", "meaning": "上线"}],
                    }
                ],
            })

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(CourseError):
            normalize_course({
                "id": "demo",
                "title": "示例",
                "sentences": [
                    {"id": "s-1", "en": "Hello there.", "zh": "你好。", "words": [{"text": "Hello", "meaning": "你好"}]},
                    {"id": "s-1", "en": "See you later.", "zh": "再见。", "words": [{"text": "later", "meaning": "稍后"}]},
                ],
            })


if __name__ == "__main__":
    unittest.main()
