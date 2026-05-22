# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.documents import Document

from rag.config import (
    RAG_CONTENT_BOOST,
    RAG_FETCH_K,
    RAG_FOLDER_BOOST,
    RAG_MAX_DISTANCE,
    RAG_TOP_K,
)

# (ключевые слова в вопросе, папка source для буста)
_FOLDER_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("парковк", "парковоч", "стоянк"), "poseshchenie_kliniki"),
    (("wi-fi", "wifi", "вай-фай", "кафетер", "гардероб", "инфраструктур", "лифт", "пандус"), "poseshchenie_kliniki"),
    (("стоит", "цена", "стоимость", "прайс", "руб"), "uslugi"),
    (("расписан", "принимает", "приём", "прием", "кардиолог", "терапевт", "гинеколог", "педиатр"), "raspisanie"),
    (("подготов", "натощак", "анализ", "кров", "гормон", "кортизол", "сдач"), "podgotovka_analizov"),
]

# При вопросе о гормонах/крови — исключить нерелевантные памятки подготовки
_PREP_EXCLUDE_IF_HORMONE: tuple[str, ...] = (
    "podgotovka_kal",
    "podgotovka_mocha",
    "podgotovka_uzi",
    "podgotovka_ekg",
    "podgotovka_krov_biohimiya",
)


@dataclass
class ScoredChunk:
    rank: int
    source_file: str
    chunk_id: str
    distance: float
    raw_distance: float
    content: str
    used_in_context: bool
    is_best: bool


@dataclass
class RetrievalResult:
    context: str
    sources: list[str]
    documents: list[Document]
    scored_chunks: list[ScoredChunk]
    best_distance: float | None
    sufficient: bool


def format_context(documents: list[Document]) -> tuple[str, list[str]]:
    sources: list[str] = []
    blocks: list[str] = []
    for i, doc in enumerate(documents, 1):
        src = doc.metadata.get("source_file", "unknown")
        if src not in sources:
            sources.append(str(src))
        blocks.append(f"[{i}] Источник: {src}\n{doc.page_content}")
    return "\n\n---\n\n".join(blocks), sources


def _question_lower(question: str) -> str:
    return question.lower().replace("ё", "е")


_OFFTOPIC_MARKERS: tuple[str, ...] = (
    "санкт-петербург",
    "санкт петербург",
    "петербург",
    "филиал",
    "бассейн",
)

_TOPIC_STOPWORDS = frozenset(
    """
    как какой какая какие когда где можно нужно нужен нужна есть ваш вашей вашего
    inmyheart клиника клиники клинике пациентов организационный вопрос приём прием
    визит работает принимает
    """.split()
)


def _context_covers_question(question: str, documents: list[Document]) -> bool:
    """Семантический порог: ключевые слова вопроса должны встречаться в найденных чанках."""
    q = _question_lower(question)
    combined = _question_lower("\n".join(doc.page_content for doc in documents))

    for marker in _OFFTOPIC_MARKERS:
        if marker in q and marker not in combined:
            return False

    tokens = [
        t for t in re.findall(r"[a-zа-яё-]{5,}", q)
        if t not in _TOPIC_STOPWORDS
    ]
    if len(tokens) < 2:
        return True

    hits = sum(1 for token in tokens if token in combined)
    return hits >= max(1, len(tokens) // 3)


def _is_relevant_chunk(question: str, doc: Document) -> bool:
    q = _question_lower(question)
    source = str(doc.metadata.get("source_file", "")).lower()

    hormone_q = any(k in q for k in ("гормон", "кортизол")) and any(
        k in q for k in ("кров", "сдач", "анализ", "подготов")
    )
    if hormone_q and "biohimiya" not in q:
        if any(ex in source for ex in _PREP_EXCLUDE_IF_HORMONE):
            return False
    return True


def _folder_boost(question: str, doc: Document) -> float:
    q = _question_lower(question)
    source = str(doc.metadata.get("source_file", ""))
    folder = str(doc.metadata.get("source_folder", ""))
    boost = 0.0

    for keywords, folder_name in _FOLDER_HINTS:
        if any(kw in q for kw in keywords):
            if folder_name in source or folder_name in folder:
                boost += RAG_FOLDER_BOOST

    content = doc.page_content.lower()
    for token in re.findall(r"[a-zа-яё0-9-]{4,}", q):
        if token in content and token not in ("клиник", "inmyheart", "можно", "нужно", "какой", "какая", "какие"):
            boost += RAG_CONTENT_BOOST * 0.35

    if "парковк" in q and "парковк" in content:
        boost += RAG_CONTENT_BOOST

    return boost


def _rerank(store, question: str, *, fetch_k: int | None = None) -> list[tuple[Document, float, float]]:
    k = fetch_k or max(RAG_FETCH_K, RAG_TOP_K)
    scored = store.similarity_search_with_score(question, k=k)
    ranked: list[tuple[Document, float, float]] = []

    for doc, raw_distance in scored:
        if not _is_relevant_chunk(question, doc):
            continue
        adjusted = float(raw_distance) - _folder_boost(question, doc)
        ranked.append((doc, adjusted, float(raw_distance)))

    ranked.sort(key=lambda item: item[1])
    return ranked[: RAG_TOP_K]


def retrieve(store, question: str, *, k: int | None = None) -> RetrievalResult:
    top_k = k or RAG_TOP_K
    ranked = _rerank(store, question, fetch_k=max(RAG_FETCH_K, top_k))
    if not ranked:
        return RetrievalResult("", [], [], [], None, False)

    documents = [doc for doc, _, _ in ranked]
    distances = [adj for _, adj, _ in ranked]
    best = min(distances)
    topic_match = _context_covers_question(question, documents)
    sufficient = best <= RAG_MAX_DISTANCE and topic_match
    used_documents = documents if sufficient else []

    scored_chunks: list[ScoredChunk] = []
    best_rank = distances.index(best) + 1
    for rank, (doc, adjusted, raw) in enumerate(ranked, 1):
        source_file = str(doc.metadata.get("source_file", "unknown"))
        chunk_id = str(doc.metadata.get("chunk_id", ""))
        scored_chunks.append(
            ScoredChunk(
                rank=rank,
                source_file=source_file,
                chunk_id=chunk_id,
                distance=adjusted,
                raw_distance=raw,
                content=doc.page_content,
                used_in_context=sufficient,
                is_best=rank == best_rank,
            )
        )

    context, sources = format_context(used_documents)
    return RetrievalResult(
        context=context,
        sources=sources if sufficient else [],
        documents=documents,
        scored_chunks=scored_chunks,
        best_distance=best,
        sufficient=sufficient,
    )
