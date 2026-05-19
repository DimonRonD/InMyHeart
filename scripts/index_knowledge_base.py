# -*- coding: utf-8 -*-
"""CLI: индексация source/ в ChromaDB."""
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

from rag.indexer import KnowledgeBaseIndexer


def main() -> None:
    parser = argparse.ArgumentParser(description="Индексация базы знаний INMYHEART в ChromaDB")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Путь к source/ (по умолчанию из SOURCE_DIR или ./source)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Удалить существующую коллекцию и переиндексировать",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только построить чанки, без записи в Chroma",
    )
    args = parser.parse_args()

    indexer = KnowledgeBaseIndexer(source_dir=args.source)

    if args.dry_run:
        chunks = indexer.build_chunks()
        by_type: dict[str, int] = {}
        for c in chunks:
            t = c.metadata.get("doc_type", "?")
            by_type[t] = by_type.get(t, 0) + 1
        print(f"Чанков: {len(chunks)}")
        for t, n in sorted(by_type.items()):
            print(f"  {t}: {n}")
        return

    stats = indexer.index(reset=args.reset)
    print("Индексация завершена.")
    print(f"  Чанков: {stats['total_chunks']}")
    print(f"  Chroma: {stats['chroma_dir']}")
    print("  По типам:", stats["by_doc_type"])
    print(f"  Манифест: {Path(stats['chroma_dir']) / 'index_manifest.json'}")


if __name__ == "__main__":
    main()
