# -*- coding: utf-8 -*-
"""Сессии пользователей Telegram (история диалога)."""
from __future__ import annotations

from rag.assistant import InMyHeartAssistant, AssistantResponse


class BotSessionManager:
    def __init__(self, assistant: InMyHeartAssistant | None = None) -> None:
        self._assistant = assistant or InMyHeartAssistant()
        self._histories: dict[int, list[tuple[str, str]]] = {}

    @property
    def assistant(self) -> InMyHeartAssistant:
        return self._assistant

    def ensure_index(self) -> int:
        return self._assistant.ensure_index()

    def reset(self, user_id: int) -> None:
        self._histories.pop(user_id, None)

    def ask(self, user_id: int, question: str) -> AssistantResponse:
        self._assistant._history = self._histories.setdefault(user_id, [])
        response = self._assistant.ask(question)
        self._histories[user_id] = self._assistant._history
        return response

    def record_exchange(self, user_id: int, question: str, answer: str) -> None:
        history = self._histories.setdefault(user_id, [])
        history.append((question, answer))


_sessions: BotSessionManager | None = None


def get_sessions() -> BotSessionManager:
    global _sessions
    if _sessions is None:
        _sessions = BotSessionManager()
    return _sessions
