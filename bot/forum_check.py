# -*- coding: utf-8 -*-
"""Проверка готовности форум-группы операторов."""
from __future__ import annotations

import logging

from telegram import Bot
from telegram.constants import ChatMemberStatus

from bot.telegram_config import operator_chat_id
from rag.config import TELEGRAM_USE_FORUM_TOPICS

logger = logging.getLogger(__name__)

TOPICS_SETUP_HINT = (
    "Выдайте боту право «Управление темами» (Manage Topics): "
    "группа → Администраторы → ваш бот → включить «Управление темами»."
)


async def verify_operator_forum(bot: Bot) -> None:
    """Логирует предупреждение, если бот не может создавать Forum Topics."""
    if not TELEGRAM_USE_FORUM_TOPICS:
        return

    group_id = operator_chat_id()
    if not group_id:
        logger.warning("TELEGRAM_OPERATOR_CHAT_ID не задан — эскалация в группу отключена")
        return

    try:
        chat = await bot.get_chat(group_id)
    except Exception as exc:
        logger.error("Не удалось получить группу операторов %s: %s", group_id, exc)
        return

    if not getattr(chat, "is_forum", False):
        logger.error(
            "Группа «%s» не форум (Topics выключены). Включите Topics в настройках группы.",
            chat.title,
        )
        return

    me = await bot.get_me()
    member = await bot.get_chat_member(group_id, me.id)

    if member.status != ChatMemberStatus.ADMINISTRATOR:
        logger.error(
            "Бот не администратор группы «%s». %s",
            chat.title,
            TOPICS_SETUP_HINT,
        )
        return

    can_manage = getattr(member, "can_manage_topics", None)
    if can_manage is False:
        logger.error(
            "Forum Topics: can_manage_topics=false в «%s». %s",
            chat.title,
            TOPICS_SETUP_HINT,
        )
    elif can_manage:
        logger.info("Forum Topics готовы: группа «%s», бот может создавать топики", chat.title)
