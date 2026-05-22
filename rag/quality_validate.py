# -*- coding: utf-8 -*-
"""Программная проверка черновика RAG-ответа (без LLM)."""
from __future__ import annotations

import re

PHONE_PATTERN = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
)

_DENIAL_PHRASES = (
    "нет информации",
    "нет данных",
    "не могу предоставить",
    "не найдено",
    "не нашёл",
    "не нашел",
    "не могу подтвердить",
)

_STOPWORDS = frozenset(
    """
    как какой какая какие когда где можно нужно нужен нужна есть ваш вашей вашего
    inmyheart клиника клиники пациентов организационный вопрос приём прием визит
    """.split()
)


def _phone_digits(text: str) -> set[str]:
    digits: set[str] = set()
    for match in PHONE_PATTERN.finditer(text):
        normalized = re.sub(r"\D", "", match.group(0))
        if len(normalized) >= 10:
            digits.add(normalized[-10:])
    return digits


def _extract_price_numbers(text: str) -> set[str]:
    numbers: set[str] = set()
    for match in re.finditer(r"\d[\d\s]{2,}\s*₽|\d{3,}", text):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 3:
            numbers.add(digits)
    return numbers


def _is_denial(draft: str) -> bool:
    lower = draft.lower()
    return any(p in lower for p in _DENIAL_PHRASES)


def validate_draft(context: str, draft: str) -> tuple[bool, str]:
    """Возвращает (ok, verdict_code)."""
    if not draft.strip():
        return False, "REJECT:EMPTY"

    draft_phones = _phone_digits(draft)
    context_phones = _phone_digits(context)
    if draft_phones - context_phones:
        return False, "REJECT:PHONE"

    if _is_denial(draft):
        return True, "APPROVE:DENIAL"

    draft_prices = _extract_price_numbers(draft)
    context_digits = re.sub(r"\D", " ", context)
    for price in draft_prices:
        if price not in context_digits.replace(" ", ""):
            if price not in re.sub(r"\D", "", context):
                return False, "REJECT:PRICE"

    return True, "APPROVE"


def strip_phones_not_in_context(draft: str, context: str) -> str:
    allowed = _phone_digits(context)

    def repl(match: re.Match[str]) -> str:
        normalized = re.sub(r"\D", "", match.group(0))
        if len(normalized) >= 10 and normalized[-10:] in allowed:
            return match.group(0)
        return ""

    cleaned = PHONE_PATTERN.sub(repl, draft)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(
        r"(?i)\b(звоните|позвоните|по телефону|телефон|напишите на email)\s*[.:]?\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    return cleaned.strip()
