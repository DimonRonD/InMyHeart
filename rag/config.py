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
