# -*- coding: utf-8 -*-
"""Сервисный слой API — общий для HTTP и Telegram."""
from __future__ import annotations

import time

from bot.db import init_db
from bot.dialog_log import log_bot_response, log_user_message
from bot.session import BotSessionManager
from rag.assistant import AssistantResponse


class AssistantApiService:
    def __init__(self) -> None:
        init_db()
        self._sessions = BotSessionManager()
        self._indexed = False

    def ensure_index(self) -> int:
        count = self._sessions.ensure_index()
        if count == 0:
            raise RuntimeError(
                "Chroma index is empty. Run: docker compose run --rm index"
            )
        self._indexed = True
        return count

    def ask(self, question: str, *, user_id: int = 0, reset_history: bool = False) -> tuple[AssistantResponse, float]:
        if reset_history:
            self._sessions.reset(user_id)

        log_user_message(user_id or 0, question, channel="api")
        started = time.perf_counter()
        response = self._sessions.ask(user_id or 0, question)
        response_ms = (time.perf_counter() - started) * 1000

        log_bot_response(
            user_id or 0,
            answer=response.answer,
            route=response.route,
            sources=response.sources,
            escalated=response.escalated,
            response_ms=response_ms,
            quality_passed=response.quality_check_passed,
            channel="api",
        )
        return response, response_ms


_service: AssistantApiService | None = None


def get_service() -> AssistantApiService:
    global _service
    if _service is None:
        _service = AssistantApiService()
        _service.ensure_index()
    return _service
