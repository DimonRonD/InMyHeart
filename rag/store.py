# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from rag.config import CHROMA_DIR, COLLECTION_NAME
from rag.models import TextChunk


def _ensure_writable_dir(path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o777)
    except OSError:
        pass


def get_vector_store(embeddings: Embeddings, *, reset: bool = False) -> Chroma:
    _ensure_writable_dir(CHROMA_DIR.parent)
    _ensure_writable_dir(CHROMA_DIR)
    if reset and CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
        _ensure_writable_dir(CHROMA_DIR)

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def add_chunks(store: Chroma, chunks: list[TextChunk], batch_size: int = 64) -> int:
    if not chunks:
        return 0

    ids = [c.chunk_id or f"chunk-{i}" for i, c in enumerate(chunks)]
    texts = [c.content for c in chunks]
    metadatas = [c.chroma_metadata() for c in chunks]

    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        store.add_texts(
            texts=texts[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )
    return len(chunks)
