# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from rag.chunking import chunk_source_directory
from rag.config import CHROMA_DIR, SOURCE_DIR
from rag.embeddings import get_embeddings
from rag.models import TextChunk
from rag.store import add_chunks, get_vector_store


def _is_chroma_readonly_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "readonly" in msg or "1032" in msg


class KnowledgeBaseIndexer:
    """Индексация source/ → ChromaDB с чанкингом по chunck_splitting.md."""

    def __init__(self, source_dir: Path | None = None, chroma_dir: Path | None = None):
        self.source_dir = Path(source_dir or SOURCE_DIR)
        self.chroma_dir = Path(chroma_dir or CHROMA_DIR)

    def build_chunks(self) -> list[TextChunk]:
        if not self.source_dir.is_dir():
            raise FileNotFoundError(f"Папка source не найдена: {self.source_dir}")
        return chunk_source_directory(self.source_dir)

    def index(self, *, reset: bool = False) -> dict:
        try:
            return self._index_once(reset=reset)
        except Exception as exc:
            if not _is_chroma_readonly_error(exc):
                raise
            if CHROMA_DIR.exists():
                shutil.rmtree(CHROMA_DIR)
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            return self._index_once(reset=True)

    def _index_once(self, *, reset: bool = False) -> dict:
        chunks = self.build_chunks()
        embeddings = get_embeddings()
        store = get_vector_store(embeddings, reset=reset)
        added = add_chunks(store, chunks)

        stats = {
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "source_dir": str(self.source_dir.resolve()),
            "chroma_dir": str(self.chroma_dir.resolve()),
            "total_chunks": added,
            "by_doc_type": dict(Counter(c.metadata.get("doc_type", "unknown") for c in chunks)),
            "by_source_file": dict(Counter(c.metadata.get("source_file", "") for c in chunks)),
        }
        self._write_manifest(chunks, stats)
        return stats

    def _write_manifest(self, chunks: list[TextChunk], stats: dict) -> None:
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.chroma_dir / "index_manifest.json"
        records = [
            {
                "chunk_id": c.chunk_id,
                "source_file": c.metadata.get("source_file"),
                "source_filename": c.metadata.get("source_filename"),
                "doc_type": c.metadata.get("doc_type"),
                "chunk_index": c.metadata.get("chunk_index"),
                "content_preview": c.content[:120].replace("\n", " "),
            }
            for c in chunks
        ]
        payload = {**stats, "chunks": records}
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
