# -*- coding: utf-8 -*-
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from rag.config import (
    EMBEDDING_PROVIDER,
    HUGGINGFACE_EMBEDDING_MODEL,
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
)

_PLACEHOLDER_MARKERS = (
    "sk-...",
    "вставьте",
    "your_openai",
    "changeme",
    "example",
)


def validate_openai_api_key(key: str | None = None) -> str:
    """Проверка ключа до запроса к API (избегаем неочевидной 401)."""
    api_key = (key or OPENAI_API_KEY or "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY не задан. Укажите ключ в файле .env "
            "(не копируйте .env.example поверх .env — там только шаблон)."
        )
    lower = api_key.lower()
    if any(m.lower() in lower for m in _PLACEHOLDER_MARKERS) or len(api_key) < 20:
        raise ValueError(
            "В .env указан шаблонный OPENAI_API_KEY, а не реальный ключ. "
            "Вставьте ключ с https://platform.openai.com/api-keys "
            "Если вы выполнили «copy .env.example .env», восстановите ключ вручную."
        )
    if not api_key.startswith("sk-"):
        raise ValueError("OPENAI_API_KEY должен начинаться с «sk-».")
    return api_key


def get_embeddings() -> Embeddings:
    if EMBEDDING_PROVIDER == "openai":
        api_key = validate_openai_api_key()
        return OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL, api_key=api_key)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as exc:
        raise ImportError(
            "EMBEDDING_PROVIDER=huggingface требует langchain-huggingface и "
            "sentence-transformers (pip install -r requirements.txt). "
            "В Docker используйте EMBEDDING_PROVIDER=openai."
        ) from exc

    return HuggingFaceEmbeddings(
        model_name=HUGGINGFACE_EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
