# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

os.environ.setdefault("DIALOG_DB_PATH", str(ROOT / "data" / "test_inmyheart.db"))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def openai_configured() -> bool:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return bool(key) and key.startswith("sk-")


@pytest.fixture(scope="session")
def assistant(openai_configured):
    if not openai_configured:
        pytest.skip("OPENAI_API_KEY not configured")
    from rag.assistant import InMyHeartAssistant
    from rag.indexer import KnowledgeBaseIndexer

    bot = InMyHeartAssistant()
    if bot.ensure_index() == 0:
        KnowledgeBaseIndexer().index(reset=True)
    return bot
