# -*- coding: utf-8 -*-
"""CLI: поиск по ChromaDB с выводом источника чанка."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from rag.config import COLLECTION_NAME
from rag.embeddings import get_embeddings
from rag.store import get_vector_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Поиск в базе знаний INMYHEART")
    parser.add_argument("query", help="Текст запроса")
    parser.add_argument("-k", type=int, default=4, help="Число результатов")
    args = parser.parse_args()

    embeddings = get_embeddings()
    store = get_vector_store(embeddings, reset=False)
    results = store.similarity_search_with_score(args.query, k=args.k)

    print(f"Коллекция: {COLLECTION_NAME}\nЗапрос: {args.query}\n")
    for i, (doc, score) in enumerate(results, 1):
        meta = doc.metadata
        print(f"--- {i} (distance={score:.4f}) ---")
        print(f"Источник: {meta.get('source_file')} [{meta.get('doc_type')}]")
        if meta.get("service_code"):
            print(f"Код услуги: {meta.get('service_code')}")
        if meta.get("chunk_index") is not None:
            print(f"Индекс чанка: {meta.get('chunk_index')}")
        print(doc.page_content[:400])
        print()


if __name__ == "__main__":
    main()
