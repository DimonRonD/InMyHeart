"""RAG: чанкинг, индексация и ChromaDB для клиники INMYHEART."""

from rag.assistant import InMyHeartAssistant
from rag.indexer import KnowledgeBaseIndexer
from rag.models import TextChunk

__all__ = ["KnowledgeBaseIndexer", "TextChunk", "InMyHeartAssistant"]
