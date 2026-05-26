# -*- coding: utf-8 -*-
"""Парсинг test_questions.md."""
from __future__ import annotations

import re
from pathlib import Path

from rag.config import PROJECT_ROOT


def parse_test_questions(path: Path | None = None) -> list[dict]:
    file_path = path or (PROJECT_ROOT / "test_questions.md")
    text = file_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n---+\n", text)
    items: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        q_match = re.search(r"\*\*Вопрос:\*\*\s*(.+)", block)
        if not q_match:
            continue
        cat_match = re.search(r"\*\*Ожидание:\*\*\s*(.+)", block)
        items.append(
            {
                "question": q_match.group(1).strip(),
                "expected": cat_match.group(1).strip() if cat_match else "",
            }
        )
    return items
