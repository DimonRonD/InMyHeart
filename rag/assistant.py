# -*- coding: utf-8 -*-
"""Оркестрация AI-ассистента INMYHEART (RAG + промпты)."""
from __future__ import annotations

from dataclasses import dataclass, field

from rag.config import ENABLE_QUALITY_CHECK
from rag.embeddings import get_embeddings
from rag.llm import chat
from rag.prompts_loader import fill, load_prompts
from rag.quality_validate import strip_phones_not_in_context, validate_draft
from rag.retrieval import RetrievalResult, retrieve
from rag.store import get_vector_store

VALID_ROUTES = {"ORG", "PII", "MED", "RESULTS", "OTHER"}

_QUALITY_REJECT_FALLBACK = (
    "К сожалению, я не могу подтвердить точность ответа по справочнику клиники. "
    "Перевожу ваше обращение на оператора — администратор регистратуры поможет вам."
)


@dataclass
class AssistantResponse:
    answer: str
    route: str
    escalated: bool
    sources: list[str] = field(default_factory=list)
    handoff_summary: str | None = None
    rag_distance: float | None = None
    retrieval: RetrievalResult | None = None
    quality_check_passed: bool | None = None
    draft_answer: str | None = None
    quality_verdict: str | None = None


class InMyHeartAssistant:
    def __init__(self) -> None:
        self.prompts = load_prompts()
        self.embeddings = get_embeddings()
        self.store = get_vector_store(self.embeddings, reset=False)
        self._history: list[tuple[str, str]] = []

    def ensure_index(self) -> int:
        """Возвращает число документов в коллекции; 0 — индекс пуст."""
        try:
            return self.store._collection.count()  # noqa: SLF001
        except Exception:
            return 0

    def classify(self, question: str) -> str:
        template = self.prompts["classifier"]
        if "Сообщение пользователя:" in template:
            system_part = template.split("Сообщение пользователя:")[0].strip()
            user_part = f"Сообщение пользователя:\n{question}"
        else:
            system_part = template
            user_part = question

        raw = chat(system_part, user_part, temperature=0).strip().upper()
        for code in ("PII", "MED", "RESULTS", "ORG", "OTHER"):
            if code in raw:
                return code
        return "OTHER"

    def _dialog_summary(self) -> str:
        if not self._history:
            return "Нет предыдущих сообщений."
        lines = [
            f"П: {q}\nО: {a[:200]}..." if len(a) > 200 else f"П: {q}\nО: {a}"
            for q, a in self._history[-5:]
        ]
        return "\n\n".join(lines)

    def _build_handoff_summary(self, route: str, question: str, bot_reply: str) -> str:
        template = self.prompts["handoff"]
        system = template.split("Категория маршрутизации:")[0].strip()
        if "Категория маршрутизации:" in template:
            user = template[template.find("Категория маршрутизации:"):]
            user = fill(user, route_category=route, dialog_summary=self._dialog_summary(), question=question)
        else:
            user = fill(
                template,
                route_category=route,
                dialog_summary=self._dialog_summary(),
                question=question,
            )
        return chat(system, user, temperature=0.2)

    def _quality_check_llm(self, context: str, draft: str) -> tuple[bool, str]:
        template = self.prompts["quality_check"]
        system = template.split("Контекст RAG:")[0].strip()
        if "Контекст RAG:" in template:
            user = template[template.find("Контекст RAG:"):]
            user = fill(user, context=context, draft_answer=draft)
        else:
            user = fill(template, context=context, draft_answer=draft)

        raw = chat(system, user, temperature=0).strip().upper()
        if "APPROVE" in raw and "REJECT" not in raw:
            return True, "APPROVE"
        if "REJECT:PHONE" in raw or "REJECT_PHONE" in raw:
            return False, "REJECT:PHONE"
        if "REJECT" in raw and "PHONE" in raw:
            return False, "REJECT:PHONE"
        return False, "REJECT"

    def _evaluate_draft(self, context: str, draft: str) -> tuple[bool, str, str]:
        """Возвращает (quality_ok, verdict, final_draft)."""
        current = draft.strip()
        prog_ok, prog_verdict = validate_draft(context, current)

        if not prog_ok and prog_verdict == "REJECT:PHONE":
            current = strip_phones_not_in_context(current, context)
            prog_ok, prog_verdict = validate_draft(context, current)

        if not prog_ok:
            return False, prog_verdict, current

        if not ENABLE_QUALITY_CHECK:
            return True, prog_verdict, current

        llm_ok, llm_verdict = self._quality_check_llm(context, current)
        if llm_ok:
            return True, llm_verdict, current

        if llm_verdict == "REJECT:PHONE":
            cleaned = strip_phones_not_in_context(current, context)
            if cleaned:
                current = cleaned
                prog_ok, prog_verdict = validate_draft(context, current)
                if prog_ok:
                    return True, "APPROVE (phone stripped)", current

        # Программная проверка пройдена — не отбрасываем корректный черновик из‑за LLM.
        return True, f"{prog_verdict} (llm override)", current

    def _quality_reject_reply(self, question: str) -> str:
        template = self.prompts.get("quality_reject")
        if template:
            if "Вопрос пользователя:" in template:
                system = template.split("Вопрос пользователя:")[0].strip()
                user = f"Вопрос пользователя:\n{question}"
                return chat(system, user, temperature=0.2)
            return chat(template, question, temperature=0.2)
        return _QUALITY_REJECT_FALLBACK

    def ask(self, question: str) -> AssistantResponse:
        question = question.strip()
        if not question:
            return AssistantResponse("Задайте, пожалуйста, ваш вопрос.", "OTHER", False)

        route = self.classify(question)

        if route == "PII":
            answer = chat(self.prompts["pii"], question, temperature=0.2)
            self._history.append((question, answer))
            return AssistantResponse(answer, route, False)

        if route in ("MED", "RESULTS"):
            answer = chat(self.prompts["medical"], question, temperature=0.2)
            summary = self._build_handoff_summary(route, question, answer)
            self._history.append((question, answer))
            return AssistantResponse(answer, route, True, handoff_summary=summary)

        if route == "OTHER":
            template = self.prompts["no_context"]
            system = template.split("Вопрос пользователя:")[0].strip()
            user = f"Вопрос пользователя:\n{question}"
            answer = chat(system, user, temperature=0.2)
            summary = self._build_handoff_summary(route, question, answer)
            self._history.append((question, answer))
            return AssistantResponse(answer, route, True, handoff_summary=summary)

        retrieval = retrieve(self.store, question)
        if not retrieval.sufficient or not retrieval.context:
            template = self.prompts["no_context"]
            system = template.split("Вопрос пользователя:")[0].strip()
            user = f"Вопрос пользователя:\n{question}"
            answer = chat(system, user, temperature=0.2)
            summary = self._build_handoff_summary("ORG_NO_RAG", question, answer)
            self._history.append((question, answer))
            return AssistantResponse(
                answer,
                "ORG",
                True,
                rag_distance=retrieval.best_distance,
                handoff_summary=summary,
                retrieval=retrieval,
            )

        sources_str = ", ".join(f"`{s}`" for s in retrieval.sources)
        system = fill(
            self.prompts["rag_system"],
            context=retrieval.context,
            sources=sources_str,
        )
        draft = chat(system, question, temperature=0.2)
        quality_ok, verdict, draft = self._evaluate_draft(retrieval.context, draft)

        if not quality_ok:
            reject_reply = self._quality_reject_reply(question)
            summary = self._build_handoff_summary("ORG_QUALITY_REJECT", question, reject_reply)
            self._history.append((question, reject_reply))
            return AssistantResponse(
                reject_reply,
                "ORG",
                True,
                sources=retrieval.sources,
                rag_distance=retrieval.best_distance,
                handoff_summary=summary,
                retrieval=retrieval,
                quality_check_passed=False,
                draft_answer=draft,
                quality_verdict=verdict,
            )

        self._history.append((question, draft))
        return AssistantResponse(
            draft,
            "ORG",
            False,
            sources=retrieval.sources,
            rag_distance=retrieval.best_distance,
            retrieval=retrieval,
            quality_check_passed=True,
            draft_answer=draft,
            quality_verdict=verdict,
        )

    def reset_history(self) -> None:
        self._history.clear()
