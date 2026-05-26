# -*- coding: utf-8 -*-
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    user_id: int = Field(default=0, ge=0, description="Ключ сессии (без ПДн)")
    reset_history: bool = False


class AskResponse(BaseModel):
    answer: str
    route: str
    escalated: bool
    sources: list[str] = Field(default_factory=list)
    response_ms: float
    quality_check_passed: bool | None = None
    rag_distance: float | None = None


class HealthResponse(BaseModel):
    status: str
    indexed_chunks: int
    api: str = "inmyheart"
