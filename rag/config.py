# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = Path(os.getenv("SOURCE_DIR", PROJECT_ROOT / "source"))
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", PROJECT_ROOT / "data" / "chroma"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "inmyheart_kb")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_OPERATOR_CHAT_ID = os.getenv("TELEGRAM_OPERATOR_CHAT_ID", "")
TELEGRAM_HANDOFF_MODE = os.getenv("TELEGRAM_HANDOFF_MODE", "notify").lower()
TELEGRAM_USE_FORUM_TOPICS = os.getenv("TELEGRAM_USE_FORUM_TOPICS", "true").lower() in ("1", "true", "yes")
TELEGRAM_FORWARD_CLIENT_MESSAGES = os.getenv("TELEGRAM_FORWARD_CLIENT_MESSAGES", "true").lower() in (
    "1",
    "true",
    "yes",
)
TELEGRAM_NEW_TOPIC_AFTER_RESET = os.getenv("TELEGRAM_NEW_TOPIC_AFTER_RESET", "false").lower() in (
    "1",
    "true",
    "yes",
)
TELEGRAM_TOPICS_FILE = os.getenv("TELEGRAM_TOPICS_FILE", "")
DIALOG_DB_PATH = os.getenv("DIALOG_DB_PATH", "")
TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC = int(os.getenv("TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC", "600"))
KPI_RESPONSE_SLA_MS = float(os.getenv("KPI_RESPONSE_SLA_MS", "5000"))
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))

OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_FETCH_K = int(os.getenv("RAG_FETCH_K", "12"))
RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "1.25"))
RAG_FOLDER_BOOST = float(os.getenv("RAG_FOLDER_BOOST", "0.12"))
RAG_CONTENT_BOOST = float(os.getenv("RAG_CONTENT_BOOST", "0.15"))
ENABLE_QUALITY_CHECK = os.getenv("ENABLE_QUALITY_CHECK", "true").lower() in ("1", "true", "yes")
HUGGINGFACE_EMBEDDING_MODEL = os.getenv(
    "HUGGINGFACE_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
