# -*- coding: utf-8 -*-
from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from rag.config import CHROMA_DIR, COLLECTION_NAME
from rag.models import TextChunk


def get_vector_store(embeddings: Embeddings, *, reset: bool = False) -> Chroma:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    if reset and CHROMA_DIR.exists():
        import shutil
        shutil.rmtree(CHROMA_DIR)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

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
