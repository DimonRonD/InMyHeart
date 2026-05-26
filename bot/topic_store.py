# -*- coding: utf-8 -*-
"""Сохранение связи Telegram user_id → forum topic (message_thread_id)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rag.config import PROJECT_ROOT, TELEGRAM_TOPICS_FILE

DEFAULT_TOPICS_FILE = PROJECT_ROOT / "data" / "telegram_client_topics.json"


def _topics_path() -> Path:
    path = Path(TELEGRAM_TOPICS_FILE) if TELEGRAM_TOPICS_FILE else DEFAULT_TOPICS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load() -> dict[str, dict]:
    path = _topics_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, dict]) -> None:
    path = _topics_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_thread_id(user_id: int) -> int | None:
    entry = _load().get(str(user_id))
    if not entry:
        return None
    thread_id = entry.get("message_thread_id")
    return int(thread_id) if thread_id is not None else None


def set_thread_id(user_id: int, message_thread_id: int, topic_name: str) -> None:
    data = _load()
    data[str(user_id)] = {
        "message_thread_id": message_thread_id,
        "topic_name": topic_name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)


def get_user_id_by_thread(message_thread_id: int) -> int | None:
    for user_id_str, entry in _load().items():
        stored = entry.get("message_thread_id")
        if stored is not None and int(stored) == message_thread_id:
            return int(user_id_str)
    return None


def clear_user(user_id: int) -> None:
    data = _load()
    if str(user_id) in data:
        del data[str(user_id)]
        _save(data)
