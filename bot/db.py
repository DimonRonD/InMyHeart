# -*- coding: utf-8 -*-
"""SQLite: диалоги, эскалации, KPI."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from rag.config import DIALOG_DB_PATH, PROJECT_ROOT

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "inmyheart.db"
_lock = Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS dialog_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'telegram',
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    route TEXT,
    sources TEXT,
    escalated INTEGER NOT NULL DEFAULT 0,
    response_ms REAL,
    quality_passed INTEGER,
    message_text TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dialog_events_user ON dialog_events(user_id);
CREATE INDEX IF NOT EXISTS idx_dialog_events_created ON dialog_events(created_at);

CREATE TABLE IF NOT EXISTS escalation_sessions (
    user_id INTEGER PRIMARY KEY,
    thread_id INTEGER,
    started_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    closed_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_escalation_active ON escalation_sessions(active, last_activity_at);

CREATE TABLE IF NOT EXISTS kpi_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    user_id INTEGER,
    route TEXT,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_kpi_created ON kpi_metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_kpi_name ON kpi_metrics(metric_name);
"""


def db_path() -> Path:
    path = Path(DIALOG_DB_PATH) if DIALOG_DB_PATH else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = sqlite3.connect(db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with db_connection() as conn:
        conn.executescript(SCHEMA)


def insert_dialog_event(
    *,
    user_id: int,
    event_type: str,
    message_text: str = "",
    route: str | None = None,
    sources: list[str] | None = None,
    escalated: bool = False,
    response_ms: float | None = None,
    quality_passed: bool | None = None,
    channel: str = "telegram",
) -> int:
    with db_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO dialog_events (
                created_at, channel, user_id, event_type, route, sources,
                escalated, response_ms, quality_passed, message_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                channel,
                user_id,
                event_type,
                route,
                json.dumps(sources or [], ensure_ascii=False),
                1 if escalated else 0,
                response_ms,
                None if quality_passed is None else (1 if quality_passed else 0),
                message_text,
            ),
        )
        return int(cur.lastrowid)


def insert_kpi_metric(
    *,
    metric_name: str,
    metric_value: float,
    user_id: int | None = None,
    route: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO kpi_metrics (created_at, metric_name, metric_value, user_id, route, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now(),
                metric_name,
                metric_value,
                user_id,
                route,
                json.dumps(details or {}, ensure_ascii=False),
            ),
        )


def upsert_escalation_session(user_id: int, *, thread_id: int | None = None) -> None:
    now = _utc_now()
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO escalation_sessions (user_id, thread_id, started_at, last_activity_at, active, closed_reason)
            VALUES (?, ?, ?, ?, 1, NULL)
            ON CONFLICT(user_id) DO UPDATE SET
                thread_id = COALESCE(excluded.thread_id, escalation_sessions.thread_id),
                last_activity_at = excluded.last_activity_at,
                active = 1,
                closed_reason = NULL
            """,
            (user_id, thread_id, now, now),
        )


def touch_escalation_session(user_id: int) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            UPDATE escalation_sessions
            SET last_activity_at = ?
            WHERE user_id = ? AND active = 1
            """,
            (_utc_now(), user_id),
        )


def get_escalation_session(user_id: int) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM escalation_sessions WHERE user_id = ? AND active = 1",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def close_escalation_session(user_id: int, reason: str) -> bool:
    with db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE escalation_sessions
            SET active = 0, closed_reason = ?, last_activity_at = ?
            WHERE user_id = ? AND active = 1
            """,
            (reason, _utc_now(), user_id),
        )
        return cur.rowcount > 0


def list_expired_escalation_sessions(timeout_seconds: int) -> list[int]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_id, last_activity_at FROM escalation_sessions
            WHERE active = 1
            """
        ).fetchall()
    expired: list[int] = []
    now = datetime.now(timezone.utc)
    for row in rows:
        last = datetime.fromisoformat(row["last_activity_at"])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).total_seconds() >= timeout_seconds:
            expired.append(int(row["user_id"]))
    return expired
