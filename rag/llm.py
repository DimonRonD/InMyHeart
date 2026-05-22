# -*- coding: utf-8 -*-
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from rag.config import LLM_TEMPERATURE, OPENAI_API_KEY, OPENAI_CHAT_MODEL
from rag.embeddings import validate_openai_api_key


def get_chat_llm(*, temperature: float | None = None) -> BaseChatModel:
    api_key = validate_openai_api_key()
    return ChatOpenAI(
        model=OPENAI_CHAT_MODEL,
        api_key=api_key,
        temperature=temperature if temperature is not None else LLM_TEMPERATURE,
    )


def chat(system: str, user: str, *, temperature: float | None = None) -> str:
    llm = get_chat_llm(temperature=temperature)
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return (response.content or "").strip()
