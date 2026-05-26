# -*- coding: utf-8 -*-
"""Запуск Telegram-бота INMYHEART."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from bot.app import run_bot


if __name__ == "__main__":
    run_bot()
