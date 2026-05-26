# -*- coding: utf-8 -*-
"""CLI AI-ассистент клиники INMYHEART (без Telegram)."""
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

from rag.assistant import InMyHeartAssistant
from rag.indexer import KnowledgeBaseIndexer
from rag.test_questions_parser import parse_test_questions
from rag.test_runner import run_test_suite


def ensure_rag_indexed() -> None:
    indexer = KnowledgeBaseIndexer()
    assistant = InMyHeartAssistant()
    count = assistant.ensure_index()
    if count == 0:
        print("Индекс RAG пуст. Выполняется индексация source/ …")
        stats = indexer.index(reset=True)
        print(f"Проиндексировано чанков: {stats['total_chunks']}\n")


def run_interactive(assistant: InMyHeartAssistant) -> None:
    print("AI-ассистент INMYHEART (CLI). Команды: /exit, /reset, /help\n")
    while True:
        try:
            question = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания.")
            break
        if not question:
            continue
        if question.lower() in ("/exit", "/quit", "выход"):
            print("До свидания.")
            break
        if question.lower() == "/reset":
            assistant.reset_history()
            print("История диалога очищена.\n")
            continue
        if question.lower() == "/help":
            print("Задайте организационный вопрос о клинике. /exit — выход, /reset — новый диалог.\n")
            continue
        _print_response(assistant.ask(question))


def _print_response(resp) -> None:
    meta = []
    meta.append(f"маршрут={resp.route}")
    if resp.sources:
        meta.append(f"источники={', '.join(resp.sources)}")
    if resp.rag_distance is not None:
        meta.append(f"distance={resp.rag_distance:.3f}")
    if resp.escalated:
        meta.append("эскалация=оператор")
    print(f"\n[{'; '.join(meta)}]")
    print(f"Ассистент: {resp.answer}\n")


from rag.test_questions_parser import parse_test_questions
    questions = parse_test_questions(path)
    if not questions:
        print(f"В {path} не найдено тестовых вопросов.")
        return
    print(f"Запуск {len(questions)} тестов из {path.name}\n")

    def _on_case(i: int, item: dict, resp) -> None:
        print(f"=== Тест {i} ===")
        print(f"Вопрос: {item['question']}")
        if item.get("expected"):
            print(f"Ожидание: {item['expected']}")
        _print_response(resp)

    log_path, result_path = run_test_suite(
        assistant,
        questions,
        root=ROOT,
        print_response=_on_case,
    )
    print(f"\nЛог сохранён: {log_path}")
    print(f"Результат AI-анализа: {result_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI AI-ассистент INMYHEART")
    parser.add_argument("-q", "--question", help="Один вопрос без интерактива")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Прогнать test_questions.md",
    )
    parser.add_argument(
        "--test-file",
        type=Path,
        default=ROOT / "test_questions.md",
        help="Путь к файлу тестов",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Переиндексировать source/ перед запуском",
    )
    parser.add_argument(
        "--skip-index-check",
        action="store_true",
        help="Не проверять наличие индекса RAG",
    )
    args = parser.parse_args()

    if args.reindex:
        print("Переиндексация source/ …")
        stats = KnowledgeBaseIndexer().index(reset=True)
        print(f"Готово: {stats['total_chunks']} чанков\n")
    elif not args.skip_index_check:
        ensure_rag_indexed()

    assistant = InMyHeartAssistant()

    if args.test:
        run_tests(assistant, args.test_file)
    elif args.question:
        _print_response(assistant.ask(args.question))
    else:
        run_interactive(assistant)


if __name__ == "__main__":
    main()
