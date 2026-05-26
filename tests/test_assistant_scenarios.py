# -*- coding: utf-8 -*-
"""Программный прогон test_questions.md + KPI в SQLite."""
from __future__ import annotations

import time

import pytest

from bot.db import init_db, insert_kpi_metric
from bot.dialog_log import log_test_accuracy
from rag.config import KPI_RESPONSE_SLA_MS, PROJECT_ROOT
from rag.test_assertions import assert_expectation
from rag.test_questions_parser import parse_test_questions


@pytest.fixture(scope="module")
def test_cases():
    cases = parse_test_questions(PROJECT_ROOT / "test_questions.md")
    assert len(cases) >= 20
    return cases


@pytest.mark.integration
@pytest.mark.slow
def test_all_scenarios(assistant, test_cases):
    init_db()
    passed = 0
    response_times_ms: list[float] = []
    failures: list[str] = []

    for index, item in enumerate(test_cases, 1):
        assistant.reset_history()
        t0 = time.perf_counter()
        response = assistant.ask(item["question"])
        response_times_ms.append((time.perf_counter() - t0) * 1000)

        result = assert_expectation(item["expected"], response)
        if result.passed:
            passed += 1
        else:
            failures.append(
                f"#{index} {item['question'][:50]}… — {', '.join(result.errors)} "
                f"(route={response.route}, escalated={response.escalated})"
            )

    total = len(test_cases)
    pass_rate = passed / total if total else 0.0

    if response_times_ms:
        avg_ms = sum(response_times_ms) / len(response_times_ms)
        insert_kpi_metric(
            metric_name="pytest_avg_response_ms",
            metric_value=avg_ms,
            details={"count": len(response_times_ms), "suite": "test_questions.md"},
        )
        sla_rate = sum(1 for ms in response_times_ms if ms <= KPI_RESPONSE_SLA_MS) / len(response_times_ms)
        insert_kpi_metric(
            metric_name="pytest_response_sla_rate",
            metric_value=sla_rate,
            details={"sla_ms": KPI_RESPONSE_SLA_MS, "avg_ms": avg_ms},
        )

    log_test_accuracy(pass_count=passed, total=total, pass_rate=pass_rate)
    insert_kpi_metric(
        metric_name="pytest_assert_pass_rate",
        metric_value=pass_rate,
        details={"passed": passed, "total": total, "failures": failures[:5]},
    )

    assert pass_rate >= 0.80, (
        f"Точность {pass_rate:.0%} ({passed}/{total}) ниже порога 80%. "
        f"Примеры: {'; '.join(failures[:3])}"
    )
