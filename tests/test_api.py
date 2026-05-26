# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.service import get_service


@pytest.fixture(scope="module")
def api_client(openai_configured):
    if not openai_configured:
        pytest.skip("OPENAI_API_KEY not configured")
    get_service().ensure_index()
    with TestClient(app) as client:
        yield client


@pytest.mark.integration
def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["indexed_chunks"] > 0


@pytest.mark.integration
def test_ask_org_question(api_client):
    response = api_client.post(
        "/ask",
        json={"question": "До скольки работает клиника в среду?", "user_id": 9001},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "ORG"
    assert data["escalated"] is False
    assert data["response_ms"] > 0
    assert len(data["answer"]) > 10


@pytest.mark.integration
def test_ask_empty_question(api_client):
    response = api_client.post("/ask", json={"question": "   "})
    assert response.status_code == 400
