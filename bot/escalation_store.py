# -*- coding: utf-8 -*-
"""Сессии эскалации: SQLite, таймаут, закрытие оператором."""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.ext import ContextTypes

from bot.db import (
    close_escalation_session,
    get_escalation_session,
    list_expired_escalation_sessions,
    touch_escalation_session,
    upsert_escalation_session,
)
from bot.dialog_log import log_deescalation
from bot.topic_store import get_thread_id
from rag.config import TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC

logger = logging.getLogger(__name__)

RETURN_TO_BOT_TEXT = (
    "Сессия с оператором завершена. Снова отвечает AI-ассистент INMYHEART.\n"
    "Задайте организационный вопрос или /operator для повторного подключения."
)
TOPIC_CLOSED_TEXT = "⏹ Сессия закрыта ({reason}). Клиент возвращён к AI-ассистенту."
TIMEOUT_REASON = "timeout_10m"
OPERATOR_CLOSE_REASON = "operator_close"


def mark_escalated(user_id: int, *, thread_id: int | None = None) -> None:
    if thread_id is None:
        thread_id = get_thread_id(user_id)
    upsert_escalation_session(user_id, thread_id=thread_id)


def touch_session(user_id: int) -> None:
    touch_escalation_session(user_id)


def is_escalated(user_id: int) -> bool:
    session = get_escalation_session(user_id)
    if not session:
        return False
    last = session["last_activity_at"]
    from datetime import datetime, timezone

    last_dt = datetime.fromisoformat(last)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
    if elapsed >= TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC:
        close_escalation_session(user_id, TIMEOUT_REASON)
        log_deescalation(user_id, reason=TIMEOUT_REASON)
        return False
    return True


def clear_escalated(user_id: int, reason: str = "reset") -> None:
    if close_escalation_session(user_id, reason):
        log_deescalation(user_id, reason=reason)


async def close_session_for_client(
    bot: Bot,
    user_id: int,
    *,
    reason: str,
    notify_client: bool = True,
    notify_topic: bool = True,
) -> bool:
    if not close_escalation_session(user_id, reason):
        return False

    log_deescalation(user_id, reason=reason)

    if notify_client:
        await bot.send_message(chat_id=user_id, text=RETURN_TO_BOT_TEXT)

    if notify_topic:
        from bot.telegram_config import operator_chat_id

        group_id = operator_chat_id()
        thread_id = get_thread_id(user_id)
        if group_id and thread_id:
            await bot.send_message(
                chat_id=group_id,
                message_thread_id=thread_id,
                text=TOPIC_CLOSED_TEXT.format(reason=reason)[:4096],
            )

    logger.info("Сессия оператора закрыта user_id=%s reason=%s", user_id, reason)
    return True


async def close_session_from_topic(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    client_id: int,
) -> bool:
    return await close_session_for_client(
        context.bot,
        client_id,
        reason=OPERATOR_CLOSE_REASON,
    )


async def process_timeouts(context: ContextTypes.DEFAULT_TYPE) -> None:
    expired = list_expired_escalation_sessions(TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC)
    for user_id in expired:
        await close_session_for_client(
            context.bot,
            user_id,
            reason=TIMEOUT_REASON,
        )
