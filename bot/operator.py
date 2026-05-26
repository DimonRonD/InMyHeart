# -*- coding: utf-8 -*-
"""Уведомление операторов и relay в Forum Topics."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.dialog_log import log_client_relay, log_escalation
from bot.escalation_store import mark_escalated, touch_session
from bot.forum_check import TOPICS_SETUP_HINT
from bot.forum_topics import send_to_client_topic
from bot.telegram_config import operator_chat_id
from rag.assistant import AssistantResponse
from rag.config import TELEGRAM_FORWARD_CLIENT_MESSAGES

logger = logging.getLogger(__name__)


def _user_label(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "неизвестный пользователь"
    parts = [f"id={user.id}"]
    if user.username:
        parts.append(f"@{user.username}")
    return ", ".join(parts)


def _username(update: Update) -> str | None:
    user = update.effective_user
    return user.username if user and user.username else None


def build_operator_alert(update: Update, question: str, response: AssistantResponse) -> str:
    lines = [
        "🚨 Эскалация INMYHEART",
        f"Пользователь: {_user_label(update)}",
        f"Маршрут: {response.route}",
        f"Вопрос: {question}",
    ]
    if response.handoff_summary:
        lines.extend(["", "📋 Резюме для оператора:", response.handoff_summary.strip()])
    if response.sources:
        lines.append(f"\nИсточники RAG: {', '.join(response.sources)}")
    lines.append("\nОтветьте в этой ветке — сообщение будет передано клиенту.")
    lines.append("Закрыть сессию: /close или /bot")
    return "\n".join(lines)


async def notify_operators(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question: str,
    response: AssistantResponse,
) -> None:
    if not operator_chat_id() or not update.effective_user:
        return

    user_id = update.effective_user.id
    username = _username(update)
    text = build_operator_alert(update, question, response)

    thread_id = await send_to_client_topic(
        context.bot,
        user_id,
        text,
        username=username,
    )

    if thread_id is None:
        fallback = (
            "⚠️ Не удалось создать топик клиента.\n"
            f"{TOPICS_SETUP_HINT}\n\n"
            f"{text}"
        )
        await context.bot.send_message(chat_id=operator_chat_id(), text=fallback[:4096])
        logger.warning("Топик не создан — сообщение отправлено в #General (нет прав Manage Topics)")

    mark_escalated(user_id, thread_id=thread_id)

    log_escalation(
        user_id,
        route=response.route,
        sources=response.sources,
        summary=response.handoff_summary,
    )


async def forward_client_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    """Пересылка сообщений клиента в его топик после эскалации."""
    if not TELEGRAM_FORWARD_CLIENT_MESSAGES or not update.effective_user:
        return
    if not get_thread_id_safe(update.effective_user.id):
        return

    user_id = update.effective_user.id
    touch_session(user_id)
    body = f"💬 Клиент {_user_label(update)}:\n{text}"
    await send_to_client_topic(
        context.bot,
        user_id,
        body,
        username=_username(update),
    )
    log_client_relay(user_id, text)


def get_thread_id_safe(user_id: int) -> int | None:
    from bot.topic_store import get_thread_id

    return get_thread_id(user_id)
