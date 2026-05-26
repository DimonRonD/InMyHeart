# -*- coding: utf-8 -*-
from __future__ import annotations

from rag.config import TELEGRAM_OPERATOR_CHAT_ID


def operator_chat_id() -> int | None:
    raw = (TELEGRAM_OPERATOR_CHAT_ID or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
