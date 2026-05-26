# -*- coding: utf-8 -*-
"""Forum Topics в группе операторов — отдельная ветка на клиента."""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.error import TelegramError

from bot.telegram_config import operator_chat_id
from bot.topic_store import clear_user, get_thread_id, set_thread_id
from rag.config import TELEGRAM_NEW_TOPIC_AFTER_RESET, TELEGRAM_USE_FORUM_TOPICS

logger = logging.getLogger(__name__)

TOPIC_NAME_MAX = 128


def build_topic_name(user_id: int, username: str | None = None) -> str:
    if username:
        name = f"Клиент @{username} · id{user_id}"
    else:
        name = f"Клиент id{user_id}"
    return name[:TOPIC_NAME_MAX]


async def ensure_client_topic(
    bot: Bot,
    user_id: int,
    *,
    username: str | None = None,
    force_new: bool = False,
) -> int | None:
    """Возвращает message_thread_id топика или None при ошибке / отключении."""
    if not TELEGRAM_USE_FORUM_TOPICS:
        return None

    group_id = operator_chat_id()
    if not group_id:
        return None

    if not force_new:
        existing = get_thread_id(user_id)
        if existing is not None:
            return existing

    topic_name = build_topic_name(user_id, username)
    try:
        topic = await bot.create_forum_topic(chat_id=group_id, name=topic_name)
        thread_id = topic.message_thread_id
        set_thread_id(user_id, thread_id, topic_name)
        logger.info("Создан топик %s для user_id=%s (thread=%s)", topic_name, user_id, thread_id)
        return thread_id
    except TelegramError as exc:
        logger.error("Не удалось создать forum topic: %s", exc)
        return get_thread_id(user_id)


async def send_to_client_topic(
    bot: Bot,
    user_id: int,
    text: str,
    *,
    username: str | None = None,
    force_new_topic: bool = False,
) -> int | None:
    """Отправляет текст в топик клиента; при необходимости создаёт топик."""
    group_id = operator_chat_id()
    if not group_id:
        return None

    thread_id = await ensure_client_topic(
        bot,
        user_id,
        username=username,
        force_new=force_new_topic,
    )

    if thread_id is None and TELEGRAM_USE_FORUM_TOPICS:
        return None

    kwargs: dict = {"chat_id": group_id, "text": text[:4096]}
    if thread_id is not None:
        kwargs["message_thread_id"] = thread_id

    await bot.send_message(**kwargs)
    return thread_id


def reset_client_topic(user_id: int) -> None:
    if TELEGRAM_NEW_TOPIC_AFTER_RESET:
        clear_user(user_id)
