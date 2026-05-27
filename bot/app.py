# -*- coding: utf-8 -*-
"""Telegram-бот AI-ассистента INMYHEART."""
from __future__ import annotations

import asyncio
import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.db import db_path, init_db
from bot.dialog_log import log_bot_response, log_escalation, log_user_message
from bot.escalation_store import (
    clear_escalated,
    is_escalated,
    process_timeouts,
)
from bot.formatting import format_user_answer, split_message
from bot.forum_check import verify_operator_forum
from bot.forum_topics import reset_client_topic
from bot.operator import forward_client_message, notify_operators
from bot.operator_request import OPERATOR_SWITCH_TEXT, is_operator_request
from bot.relay import operator_close_command, relay_operator_message
from bot.session import get_sessions
from bot.telegram_config import operator_chat_id
from rag.assistant import AssistantResponse
from rag.config import TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC
from rag.embeddings import validate_openai_api_key

logger = logging.getLogger(__name__)

CLIENT_RELAY_ACK = "Ваше сообщение передано оператору. Ожидайте ответ."
PREPARING_TEXT = "Бот готовит ответ..."
WELCOME = (
    "Здравствуйте! Я AI-ассистент клиники INMYHEART.\n\n"
    "Помогаю с организационными вопросами: запись, расписание, подготовка к анализам, "
    "услуги и правила посещения.\n\n"
    "Команды:\n"
    "/help — подсказка\n"
    "/reset — начать диалог заново\n"
    "/operator — запросить оператора"
)
HELP_TEXT = (
    "Задайте вопрос текстом. Не указывайте ФИО, адрес, телефон и другие персональные данные.\n\n"
    "По медицинским вопросам и результатам анализов я переведу обращение на оператора."
)

TIMEOUT_JOB_NAME = "operator_session_timeout"


def ensure_rag_indexed() -> None:
    sessions = get_sessions()
    count = sessions.ensure_index()
    if count == 0:
        raise RuntimeError(
            "RAG index empty. Start stack with: docker compose up -d (runs index service first)"
        )
    logger.info("RAG index ready: %s chunks", count)


async def _send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


def _operator_handoff_response(question: str, *, via_command: bool = False) -> AssistantResponse:
    if via_command:
        summary = f"Пользователь запросил оператора через /operator.\nСообщение: {question}"
    else:
        summary = f"Пользователь запросил оператора.\nСообщение: {question}"
    return AssistantResponse(
        answer=OPERATOR_SWITCH_TEXT,
        route="OPERATOR",
        escalated=True,
        handoff_summary=summary,
    )


async def _escalate_to_operator(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question: str,
    *,
    via_command: bool = False,
) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    log_user_message(user_id, question)
    response = _operator_handoff_response(question, via_command=via_command)
    get_sessions().record_exchange(user_id, question, response.answer)

    await update.message.reply_text(OPERATOR_SWITCH_TEXT)
    await notify_operators(update, context, question, response)


async def _process_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    question: str,
    *,
    force_escalate: bool = False,
) -> None:
    if not update.message:
        return

    user_id = update.effective_user.id
    log_user_message(user_id, question)

    if is_escalated(user_id) and not force_escalate:
        get_sessions().record_exchange(user_id, question, CLIENT_RELAY_ACK)
        await update.message.reply_text(CLIENT_RELAY_ACK)
        await forward_client_message(update, context, question)
        return

    chat_id = update.effective_chat.id
    await _send_typing(context, chat_id)
    status_msg = await update.message.reply_text(PREPARING_TEXT)

    started = time.perf_counter()
    try:
        await _send_typing(context, chat_id)
        response = await asyncio.to_thread(get_sessions().ask, user_id, question)
        if force_escalate and not response.escalated:
            from dataclasses import replace

            response = replace(
                response,
                escalated=True,
                handoff_summary=response.handoff_summary
                or f"Пользователь запросил оператора вручную.\nПоследний вопрос: {question}",
            )
    except Exception:
        logger.exception("Ошибка ассистента")
        await status_msg.edit_text(
            "Произошла ошибка при обработке запроса. Попробуйте позже или обратитесь в регистратуру."
        )
        return

    response_ms = (time.perf_counter() - started) * 1000
    answer_text = format_user_answer(response)
    try:
        await status_msg.delete()
    except Exception:
        pass

    for chunk in split_message(answer_text):
        await update.message.reply_text(chunk)

    log_bot_response(
        user_id,
        answer=answer_text,
        route=response.route,
        sources=response.sources,
        escalated=response.escalated,
        response_ms=response_ms,
        quality_passed=response.quality_check_passed,
    )

    if response.escalated:
        await notify_operators(update, context, question, response)
    elif is_escalated(user_id):
        await forward_client_message(update, context, question)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    get_sessions().reset(user_id)
    clear_escalated(user_id, reason="reset")
    reset_client_topic(user_id)
    await update.message.reply_text(
        "История диалога очищена. Можете задать новый вопрос."
    )


async def operator_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text.strip() if update.message and update.message.text else "/operator"
    await _escalate_to_operator(update, context, question, via_command=True)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if not text:
        return
    if is_operator_request(text):
        await _escalate_to_operator(update, context, text)
        return
    await _process_question(update, context, text)


def _operator_group_filter():
    group_id = operator_chat_id()
    if group_id is None:
        return filters.Chat(-1)
    return filters.Chat(chat_id=group_id)


async def _post_init(app: Application) -> None:
    init_db()
    logger.info(
        "SQLite: логи диалогов и KPI (%s), таймаут оператора %s с",
        db_path(),
        TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC,
    )
    await verify_operator_forum(app.bot)
    if app.job_queue:
        app.job_queue.run_repeating(process_timeouts, interval=60, first=30, name=TIMEOUT_JOB_NAME)


def build_application() -> Application:
    token = (TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env")
    validate_openai_api_key()
    ensure_rag_indexed()

    app = Application.builder().token(token).post_init(_post_init).build()
    op_filter = _operator_group_filter()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("operator", operator_command))
    app.add_handler(CommandHandler("close", operator_close_command, filters=op_filter), group=0)
    app.add_handler(CommandHandler("bot", operator_close_command, filters=op_filter), group=0)
    app.add_handler(
        MessageHandler(op_filter & filters.TEXT & ~filters.COMMAND, relay_operator_message),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, text_message),
        group=1,
    )
    return app


def run_bot() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    app = build_application()
    logger.info("Telegram-бот INMYHEART запущен (polling)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
