# -*- coding: utf-8 -*-
from __future__ import annotations

from rag.assistant import AssistantResponse

TG_MAX_LENGTH = 4096


def format_user_answer(response: AssistantResponse) -> str:
    parts = [response.answer.strip()]
    if response.sources and not response.escalated:
        parts.append(f"\n\n📎 Источники: {', '.join(response.sources)}")
    if response.escalated:
        parts.append(
            "\n\n👤 Если нужна помощь оператора — дождитесь ответа или позвоните в регистратуру."
        )
    return "".join(parts).strip()


def split_message(text: str, limit: int = TG_MAX_LENGTH) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        split_at = text.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return [c for c in chunks if c]
