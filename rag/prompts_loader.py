# -*- coding: utf-8 -*-
"""Загрузка промптов из prompts.md."""
from __future__ import annotations

import re
from pathlib import Path

from rag.config import PROJECT_ROOT

PROMPTS_FILE = PROJECT_ROOT / "prompts.md"

_SECTION_KEYS: list[tuple[str, str]] = [
    ("## 1.", "classifier"),
    ("## 2.", "rag_system"),
    ("## 3.", "pii"),
    ("## 4.", "medical"),
    ("## 5.", "no_context"),
    ("## 6.", "handoff"),
    ("## 7.", "quality_check"),
    ("## 7.1.", "quality_reject"),
]


def _extract_codeblock(section_text: str) -> str:
    match = re.search(r"```\n(.*?)```", section_text, re.DOTALL)
    if not match:
        raise ValueError("В секции prompts.md не найден блок ``` ... ```")
    return match.group(1).strip()


def load_prompts(path: Path | None = None) -> dict[str, str]:
    text = (path or PROMPTS_FILE).read_text(encoding="utf-8")
    prompts: dict[str, str] = {}
    for i, (header, key) in enumerate(_SECTION_KEYS):
        start = text.find(header)
        if start == -1:
            raise ValueError(f"Секция не найдена: {header}")
        next_header = _SECTION_KEYS[i + 1][0] if i + 1 < len(_SECTION_KEYS) else "## 8."
        end = text.find(next_header, start + 1) if next_header else len(text)
        if end == -1:
            end = len(text)
        prompts[key] = _extract_codeblock(text[start:end])
    return prompts


def fill(template: str, **kwargs: str) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", value or "")
    return result
