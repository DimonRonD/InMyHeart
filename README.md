# InMyHeart — AI-ассистент медицинской клиники

RAG-ассистент на базе **LangChain**, **ChromaDB** и **OpenAI** для ответов на организационные вопросы пациентов клиники INMYHEART.  
Отвечает только по документам из `source/`, маршрутизирует обращения (организационные / ПДн / медицинские) и эскалирует на оператора при необходимости.

**Текущий этап:** CLI + **FastAPI** + **Telegram-бот** (Forum Topics, relay, SQLite-логи).

## Возможности

- **RAG** — поиск по базе знаний с rerank, бустом по типу документа и фильтрацией нерелевантных чанков
- **Маршрутизация** — классификатор из `prompts.md` (ORG / PII / MED / RESULTS / OTHER)
- **Quality check** — программная проверка черновика + LLM post-check
- **CLI** — интерактив, одиночный вопрос, прогон тестов с AI-анализом
- **FastAPI** — `/health`, `/ask` (общая точка для бота и будущего веб-чата)
- **Telegram** — polling, Forum Topics, relay оператор ↔ клиент, таймаут сессии 10 мин
- **SQLite** — логи диалогов (без ПДн), KPI времени ответа и SLA ≤ 5 с
- **pytest** — программные assert'ы по `test_questions.md` + KPI в CI

> **Данные `source/`:** синтетические документы для MVP — см. [`source/DATA_NOTICE.md`](source/DATA_NOTICE.md).

## Архитектура

```
Клиент (Telegram / HTTP / CLI)
        ↓
   /ask или bot handler
        ↓
   классификатор (prompts §1)
        ├─ PII → отказ
        ├─ MED/RESULTS/OTHER → эскалация → Forum Topic → relay
        └─ ORG → RAG → quality check → ответ / эскалация
        ↓
   SQLite (dialog_events, kpi_metrics, escalation_sessions)
```

## Структура проекта

| Путь | Назначение |
|------|------------|
| `source/` | База знаний (демо-данные, см. DATA_NOTICE.md) |
| `rag/` | RAG, ассистент, тесты, assertions |
| `api/` | FastAPI `/health`, `/ask` |
| `bot/` | Telegram-бот, relay, SQLite-логи |
| `tests/` | pytest + KPI |
| `data/chroma/` | Chroma (не в git) |
| `data/inmyheart.db` | SQLite prod (не в git) |

## Быстрый старт

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # только если .env ещё нет
python scripts/index_knowledge_base.py --reset
```

### CLI

```bash
python scripts/assistant_cli.py
python scripts/assistant_cli.py -q "До скольки работает клиника в среду?"
python scripts/assistant_cli.py --test
```

### FastAPI

```bash
python scripts/run_api.py
# GET  http://127.0.0.1:8000/health
# POST http://127.0.0.1:8000/ask  {"question": "...", "user_id": 1}
```

### Telegram

```bash
python scripts/telegram_bot.py
```

### pytest (CI)

```bash
pytest tests/ -m integration -v
```

## Переменные окружения

Полный список — [`.env.example`](.env.example).

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OPENAI_API_KEY` | — | Ключ OpenAI |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | FastAPI |
| `DIALOG_DB_PATH` | `data/inmyheart.db` | SQLite логи и KPI |
| `TELEGRAM_OPERATOR_SESSION_TIMEOUT_SEC` | `600` | Таймаут сессии оператора |
| `KPI_RESPONSE_SLA_MS` | `5000` | SLA времени ответа |

## Дальнейшие шаги

- [x] Telegram-бот + Forum Topics + relay
- [x] FastAPI `/health`, `/ask`
- [x] SQLite-логи и KPI
- [x] pytest по `test_questions.md`
- [ ] Веб-чат (HTML/JS → `/ask`)
- [ ] Замена синтетических документов на регламенты клиники

## Ссылки

- Репозиторий: https://github.com/DimonRonD/InMyHeart.git
- Операторы: [`operator_handoff.md`](operator_handoff.md)
- Стек: [`stek.md`](stek.md)
- **Статус vs ТЗ:** [`TZ_STATUS.md`](TZ_STATUS.md)
