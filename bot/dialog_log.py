# -*- coding: utf-8 -*-
"""Логирование диалогов и KPI в SQLite (без ПДн)."""
from __future__ import annotations

from bot.db import insert_dialog_event, insert_kpi_metric
from bot.pii_redact import redact_for_log
from rag.config import KPI_RESPONSE_SLA_MS

EVENT_USER_MESSAGE = "user_message"
EVENT_BOT_RESPONSE = "bot_response"
EVENT_OPERATOR_REPLY = "operator_reply"
EVENT_ESCALATION = "escalation"
EVENT_DEESCALATION = "deescalation"
EVENT_CLIENT_RELAY = "client_relay"


def log_user_message(user_id: int, text: str, *, channel: str = "telegram") -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_USER_MESSAGE,
        message_text=redact_for_log(text),
        channel=channel,
    )


def log_bot_response(
    user_id: int,
    *,
    answer: str,
    route: str,
    sources: list[str] | None,
    escalated: bool,
    response_ms: float,
    quality_passed: bool | None = None,
    channel: str = "telegram",
) -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_BOT_RESPONSE,
        message_text=redact_for_log(answer),
        route=route,
        sources=sources,
        escalated=escalated,
        response_ms=response_ms,
        quality_passed=quality_passed,
        channel=channel,
    )
    sla_ok = 1.0 if response_ms <= KPI_RESPONSE_SLA_MS else 0.0
    insert_kpi_metric(
        metric_name="response_time_ms",
        metric_value=response_ms,
        user_id=user_id,
        route=route,
        details={"sla_ms": KPI_RESPONSE_SLA_MS},
    )
    insert_kpi_metric(
        metric_name="response_time_sla_ok",
        metric_value=sla_ok,
        user_id=user_id,
        route=route,
        details={"sla_ms": KPI_RESPONSE_SLA_MS, "response_ms": response_ms},
    )
    if quality_passed is not None:
        insert_kpi_metric(
            metric_name="quality_check_pass",
            metric_value=1.0 if quality_passed else 0.0,
            user_id=user_id,
            route=route,
        )


def log_escalation(
    user_id: int,
    *,
    route: str,
    sources: list[str] | None = None,
    summary: str | None = None,
) -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_ESCALATION,
        message_text=redact_for_log(summary or ""),
        route=route,
        sources=sources,
        escalated=True,
    )
    insert_kpi_metric(
        metric_name="escalation",
        metric_value=1.0,
        user_id=user_id,
        route=route,
    )


def log_deescalation(user_id: int, *, reason: str) -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_DEESCALATION,
        message_text=redact_for_log(reason),
        escalated=False,
    )


def log_operator_reply(user_id: int, text: str, *, delivered: bool) -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_OPERATOR_REPLY,
        message_text=redact_for_log(text),
        escalated=True,
    )
    insert_kpi_metric(
        metric_name="operator_relay_ok",
        metric_value=1.0 if delivered else 0.0,
        user_id=user_id,
    )


def log_client_relay(user_id: int, text: str) -> None:
    insert_dialog_event(
        user_id=user_id,
        event_type=EVENT_CLIENT_RELAY,
        message_text=redact_for_log(text),
        escalated=True,
    )


def log_test_accuracy(*, pass_count: int, total: int, pass_rate: float) -> None:
    insert_kpi_metric(
        metric_name="test_accuracy_pass_rate",
        metric_value=pass_rate,
        details={"pass_count": pass_count, "total": total},
    )
    insert_kpi_metric(
        metric_name="test_accuracy_pass_count",
        metric_value=float(pass_count),
        details={"total": total},
    )
