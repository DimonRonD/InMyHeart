# -*- coding: utf-8 -*-
"""FastAPI — /health и /ask для бота и будущего веб-чата."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from api.schemas import AskRequest, AskResponse, HealthResponse
from api.service import get_service

app = FastAPI(
    title="INMYHEART AI Assistant API",
    version="1.0.0",
    description="REST API RAG-ассистента клиники INMYHEART",
)


@app.on_event("startup")
def startup() -> None:
    get_service().ensure_index()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    count = get_service().ensure_index()
    return HealthResponse(status="ok", indexed_chunks=count)


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is empty")

    response, response_ms = get_service().ask(
        question,
        user_id=body.user_id,
        reset_history=body.reset_history,
    )
    return AskResponse(
        answer=response.answer,
        route=response.route,
        escalated=response.escalated,
        sources=response.sources,
        response_ms=round(response_ms, 2),
        quality_check_passed=response.quality_check_passed,
        rag_distance=response.rag_distance,
    )
