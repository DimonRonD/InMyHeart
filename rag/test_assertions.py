# -*- coding: utf-8 -*-
"""Программные проверки test_questions.md против AssistantResponse."""
from __future__ import annotations

from dataclasses import dataclass

from rag.assistant import AssistantResponse


@dataclass
class TestAssertionResult:
    passed: bool
    errors: list[str]


def _allowed_routes(expected: str) -> set[str] | None:
    upper = expected.upper()
    if "RESULTS/PII" in upper or "PII/RESULTS" in upper:
        return {"PII", "RESULTS"}
    if "PII" in upper and "RESULTS" in upper and ("ИЛИ" in upper or "/" in expected):
        return {"PII", "RESULTS"}

    routes: set[str] = set()
    for code in ("ORG", "PII", "MED", "RESULTS", "OTHER", "OPERATOR"):
        if code in upper:
            routes.add(code)
    return routes or None


def _must_escalate(expected: str, allowed: set[str] | None) -> bool:
    lower = expected.lower()
    if "эскалац" in lower or "оператор" in lower:
        return True
    if "нет в rag" in lower:
        return True
    if allowed and allowed <= {"MED"}:
        return True
    if allowed and allowed <= {"RESULTS"}:
        return True
    if "OTHER" in (allowed or set()) and "или" in lower:
        return True
    if allowed and "RESULTS" in allowed and "PII" not in allowed:
        return True
    return False


def _must_not_escalate(expected: str, allowed: set[str] | None) -> bool:
    if not allowed or allowed != {"ORG"}:
        return False
    lower = expected.lower()
    return "эскалац" not in lower and "оператор" not in lower


def assert_expectation(expected: str, response: AssistantResponse) -> TestAssertionResult:
    errors: list[str] = []
    allowed = _allowed_routes(expected)

    if allowed and "OTHER" in allowed and "ИЛИ" in expected.upper():
        if response.route not in allowed and not response.escalated:
            errors.append(f"маршрут {response.route}, ожидалось {sorted(allowed)} или эскалация")
    elif allowed and response.route not in allowed:
        if not (response.escalated and "OTHER" in allowed):
            errors.append(f"маршрут {response.route}, ожидалось одно из {sorted(allowed)}")

    if _must_escalate(expected, allowed) and not response.escalated:
        errors.append("ожидалась эскалация на оператора")

    if _must_not_escalate(expected, allowed) and response.escalated:
        errors.append("ORG без эскалации: получена эскалация")

    if "PII" in expected.upper():
        answer_lower = response.answer.lower()
        for token in ("иванов", "петров", "сидоров", "ivanov@mail.ru", "ул.", "ленина", "мира 10"):
            if token in answer_lower:
                errors.append(f"ответ содержит ПДн-подобный фрагмент: {token}")

    if "MED" in expected.upper():
        if any(w in response.answer.lower() for w in ("принимайте", "назнач", "мг ", "таблетк")):
            errors.append("мед. ответ не должен назначать лечение")

    return TestAssertionResult(passed=not errors, errors=errors)
