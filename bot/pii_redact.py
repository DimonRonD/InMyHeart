# -*- coding: utf-8 -*-
"""Маскирование ПДн перед записью в логи."""
from __future__ import annotations

import re

_PHONE = re.compile(
    r"(?:\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}|"
    r"\b\d{3}[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}\b"
)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b", re.IGNORECASE)
_FIO = re.compile(
    r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b"
)
_PASSPORT = re.compile(r"\b\d{4}\s?\d{6}\b")
_SNILS = re.compile(r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b")
_BIRTHDATE = re.compile(r"\b\d{2}[./]\d{2}[./]\d{4}\b")


def redact_for_log(text: str | None, *, max_len: int = 2000) -> str:
    if not text:
        return ""
    value = text.strip()[:max_len]
    value = _PHONE.sub("[ТЕЛЕФОН]", value)
    value = _EMAIL.sub("[EMAIL]", value)
    value = _PASSPORT.sub("[ПАСПОРТ]", value)
    value = _SNILS.sub("[СНИЛС]", value)
    value = _BIRTHDATE.sub("[ДАТА]", value)
    value = _FIO.sub("[ФИО]", value)
    return value
