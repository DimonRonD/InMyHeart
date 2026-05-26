# -*- coding: utf-8 -*-
"""Relay: ответ оператора в Forum Topic → личный чат клиента."""
from __future__ import annotations

import logging

from telegram import ReactionTypeEmoji, Update
from telegram.ext import ContextTypes

from bot.dialog_log import log_operator_reply
from bot.escalation_store import close_session_from_topic, touch_session
from bot.session import get_sessions
from bot.telegram_config import operator_chat_id
from bot.topic_store import get_user_id_by_thread
from rag.config import TELEGRAM_USE_FORUM_TOPICS

logger = logging.getLogger(__name__)

OPERATOR_REPLY_PREFIX = "👤 Оператор:"
RETURN_PHRASES = frozenset({"вернуть к боту", "вернуть к ассистенту"})


async def _confirm_delivery(message) -> None:
    try:
        await message.set_reaction([ReactionTypeEmoji("✅")])
    except Exception:
        logger.warning("Не удалось поставить реакцию ✅ на сообщение оператора")


async def relay_operator_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пересылает текст оператора из топика клиенту."""
    if not TELEGRAM_USE_FORUM_TOPICS:
        return

    message = update.message
    group_id = operator_chat_id()
    if not message or not message.text or not group_id:
        return
    if update.effective_chat.id != group_id:
        return
    if message.from_user and message.from_user.is_bot:
        return

    thread_id = message.message_thread_id
    if not thread_id:
        return

    client_id = get_user_id_by_thread(thread_id)
    if client_id is None:
        return

    text = message.text.strip()
    if not text:
        return

    lowered = text.lower()
    if lowered in RETURN_PHRASES:
        ok = await close_session_from_topic(context, client_id=client_id)
        if ok and message:
            await message.reply_text("✅ Клиент возвращён к AI-ассистенту.")
        elif message:
            await message.reply_text("Активной сессии с оператором нет.")
        return

    body = f"{OPERATOR_REPLY_PREFIX}\n{text}"
    delivered = False
    try:
        await context.bot.send_message(chat_id=client_id, text=body[:4096])
        delivered = True
        touch_session(client_id)
        get_sessions().record_exchange(client_id, "—", body)
        await _confirm_delivery(message)
    except Exception:
        logger.exception("Ошибка relay оператор → клиент user_id=%s", client_id)

    log_operator_reply(client_id, text, delivered=delivered)
    if delivered:
        logger.info("Relay оператор → клиент user_id=%s (thread=%s)", client_id, thread_id)


async def operator_close_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.message_thread_id:
        if message:
            await message.reply_text("Команда работает только в топике клиента.")
        return

    client_id = get_user_id_by_thread(message.message_thread_id)
    if client_id is None:
        await message.reply_text("Топик не привязан к клиенту.")
        return

    ok = await close_session_from_topic(context, client_id=client_id)
    if ok:
        await message.reply_text("✅ Клиент возвращён к AI-ассистенту.")
        await _confirm_delivery(message)
    else:
        await message.reply_text("Активной сессии с оператором нет.")
