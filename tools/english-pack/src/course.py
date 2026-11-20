"""课程 JSON 的读取与校验。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

COURSE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SENTENCE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CourseError(ValueError):
    """课程数据不合法。"""


def _as_text(value: Any, field: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CourseError(f"{field} 必须是字符串")
    return value.strip()


def _require(value: str, field: str) -> str:
    text = _as_text(value, field)
    if not text:
        raise CourseError(f"缺少 {field}")
    return text


def _word_in_sentence(word: str, sentence: str) -> bool:
    return word.casefold() in sentence.casefold()


def normalize_words(raw_words: Any, *, sentence_en: str, where: str) -> list[dict[str, str]]:
    if raw_words is None:
        words_in = []
    elif not isinstance(raw_words, list):
        raise CourseError(f"{where} 的 words 必须是列表")
    else:
        words_in = raw_words

    words: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, item in enumerate(words_in, 1):
        if isinstance(item, str):
            text = item.strip()
            meaning = ""
        elif isinstance(item, dict):
            text = _as_text(item.get("text"), f"{where} 第 {i} 个词条 text")
            meaning = _as_text(item.get("meaning"), f"{where} 第 {i} 个词条 meaning")
        else:
            raise CourseError(f"{where} 第 {i} 个词条格式不对")
        if not text:
            raise CourseError(f"{where} 第 {i} 个词条缺少 text")
        key = text.casefold()
        if key in seen:
            raise CourseError(f"{where} 词条重复：{text}")
        seen.add(key)
        if not _word_in_sentence(text, sentence_en):
            raise CourseError(f"{where} 词条「{text}」未出现在英文原句中")
        words.append({"text": text, "meaning": meaning})
    return words


def normalize_sentence(raw: Any, index: int) -> dict[str, Any]:
    where = f"第 {index} 句"
    if not isinstance(raw, dict):
        raise CourseError(f"{where} 不是对象")
    sentence_id = _require(raw.get("id"), f"{where} id")
    if not SENTENCE_ID_RE.match(sentence_id):
        raise CourseError(f"{where} id 只能用小写字母、数字和连字符：{sentence_id}")
    en = _require(raw.get("en"), f"{where} en")
    zh = _require(raw.get("zh"), f"{where} zh")
    audio = _as_text(raw.get("audio"), f"{where} audio")
    if audio:
        audio_path = Path(audio)
        if audio_path.is_absolute() or ".." in audio_path.parts:
            raise CourseError(f"{where} audio 必须是相对路径，且不能包含 ..")
    return {
        "id": sentence_id,
        "en": en,
        "zh": zh,
        "note": _as_text(raw.get("note"), f"{where} note"),
        "audio": audio,
        "words": normalize_words(raw.get("words"), sentence_en=en, where=where),
    }


def normalize_course(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CourseError("课程 JSON 根节点必须是对象")
    course_id = _require(data.get("id"), "id")
    if not COURSE_ID_RE.match(course_id):
        raise CourseError(f"课程 id 只能用小写字母、数字和连字符：{course_id}")
    raw_sentences = data.get("sentences")
    if not isinstance(raw_sentences, list) or not raw_sentences:
        raise CourseError("课程需要非空的 sentences 列表")

    sentences: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_sentences, 1):
        sentence = normalize_sentence(raw, i)
        if sentence["id"] in seen_ids:
            raise CourseError(f"句子 id 重复：{sentence['id']}")
        seen_ids.add(sentence["id"])
        sentences.append(sentence)

    return {
        "id": course_id,
        "title": _require(data.get("title"), "title"),
        "subtitle": _as_text(data.get("subtitle"), "subtitle") or "一句一句听，再跟读",
        "description": _as_text(data.get("description"), "description"),
        "sentences": sentences,
    }


def load_course(path: Path) -> dict[str, Any]:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise CourseError(f"找不到课程文件：{source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CourseError(f"课程 JSON 无法解析：{err}") from err
    return normalize_course(data)
