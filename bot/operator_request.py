# -*- coding: utf-8 -*-
"""Определение явного запроса оператора / живого человека."""
from __future__ import annotations

import re

OPERATOR_SWITCH_TEXT = "Переключаю на оператора."

# Явные формулировки без LLM: «позовите оператора», «хочу человека», /operator и т.п.
_OPERATOR_REQUEST = re.compile(
    r"""
    (?:
        /operator\b
        |
        (?:позов\w*|вызов\w*|соедин\w*|переключ\w*|перевед\w*|дай\w*|дайте|нуж\w*|хоч\w*)
        \s+(?:\w+\s+){0,2}?
        (?:оператор\w*|администратор\w*|жив\w+\s+человек\w*|человек\w*)
        |
        (?:поговор\w*|общ\w*|связ\w*)\s+с\s+
        (?:оператор\w*|администратор\w*|человек\w*|жив\w+\s+человек\w*)
        |
        (?:оператор\w*|администратор\w*)\s+(?:нуж\w*|есть\w*|сейчас|онлайн|online)
        |
        (?:можно|есть|где)\s+(?:оператор\w*|администратор\w*|жив\w+\s+человек\w*)
        |
        переключ\w*\s+на\s+(?:оператор\w*|администратор\w*|человек\w*)
    )
    """,
    re.IGNORECASE | re.UNICODE | re.VERBOSE,
)


def is_operator_request(text: str) -> bool:
    normalized = (text or "").strip()
    if not normalized:
        return False
    return bool(_OPERATOR_REQUEST.search(normalized))
