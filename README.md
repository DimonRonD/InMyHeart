# InMyHeart — AI-ассистент медицинской клиники

RAG-ассистент на базе **LangChain**, **ChromaDB** и **OpenAI** для ответов на организационные вопросы пациентов клиники INMYHEART.  
Отвечает только по документам из `source/`, маршрутизирует обращения (организационные / ПДн / медицинские) и эскалирует на оператора при необходимости.

**Текущий этап:** CLI-ассистент (без Telegram-бота).

## Возможности

- **RAG** — поиск по базе знаний с rerank, бустом по типу документа и фильтрацией нерелевантных чанков
- **Маршрутизация** — классификатор из `prompts.md` (ORG / PII / MED / RESULTS / OTHER)
- **Промпты** — системные инструкции загружаются из `prompts.md` в runtime
- **Quality check** — программная проверка черновика + опциональный LLM post-check
- **CLI** — интерактивный режим, одиночный вопрос, прогон тестов с логами
- **Тестирование** — `test_questions.md` → `test_log_YYYYMMDD.txt` + AI-анализ → `test_result_YYYYMMDD.txt`

## Архитектура (кратко)

```
Вопрос → классификатор (prompts §1)
  ├─ PII      → отказ без обработки ПДн
  ├─ MED/RESULTS → эскалация на оператора
  ├─ OTHER    → «нет в базе» → оператор
  └─ ORG      → Chroma RAG → ответ по контексту (prompts §2)
                    └─ quality check → при сбое эскалация (§7.1), не «нет данных»
```

Подробнее: [`stek.md`](stek.md), [`prompts.md`](prompts.md).

## Структура проекта

| Путь | Назначение |
|------|------------|
| `source/` | База знаний: FAQ, услуги, расписание, подготовка к анализам, памятки |
| `rag/` | Чанкинг, эмбеддинги, Chroma, retrieval, ассистент, тест-раннер |
| `scripts/` | CLI, индексация, генерация source, отладочный поиск |
| `prompts.md` | Системные промпты (классификатор, RAG, PII, эскалация, quality check) |
| `test_questions.md` | 23 тестовых сценария для `--test` |
| `chunck_splitting.md` | Правила разбиения документов на чанки |
| `stek.md` | Описание технологического стека |
| `data/chroma/` | Векторная БД (не в git) |

### Модули `rag/`

| Файл | Роль |
|------|------|
| `assistant.py` | Оркестрация: маршрут → RAG → ответ / эскалация |
| `retrieval.py` | Поиск, rerank, буст по папке, фильтр релевантности |
| `quality_validate.py` | Программная проверка черновика (телефоны, цены) |
| `prompts_loader.py` | Загрузка промптов из `prompts.md` |
| `llm.py` | Вызов OpenAI Chat |
| `test_runner.py` | Прогон тестов, лог, AI-оценка качества |
| `chunking.py`, `indexer.py`, `store.py` | Индексация source → Chroma |

### Скрипты `scripts/`

| Скрипт | Назначение |
|--------|------------|
| `assistant_cli.py` | **Основной CLI-ассистент** |
| `index_knowledge_base.py` | Индексация `source/` в Chroma |
| `query_knowledge_base.py` | Отладочный similarity-поиск |
| `generate_source_docs.py` | Генерация тестовых документов в `source/` |

## Быстрый старт

### 1. Окружение

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Конфигурация

Создайте `.env` на основе `.env.example` и укажите **реальный** `OPENAI_API_KEY`.

> **Важно:** не выполняйте `copy .env.example .env`, если `.env` уже настроен — шаблон перезапишет ключ значением `sk-...`.

Минимально необходимо:

```env
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
```

### 3. Индексация базы знаний

```bash
python scripts/index_knowledge_base.py --reset
```

После изменения файлов в `source/` переиндексируйте:

```bash
python scripts/index_knowledge_base.py --reset
# или
python scripts/assistant_cli.py --reindex
```

### 4. Запуск ассистента

```bash
# Интерактивный режим (команды: /exit, /reset, /help)
python scripts/assistant_cli.py

# Один вопрос
python scripts/assistant_cli.py -q "До скольки работает клиника в среду?"

# Прогон тестов
python scripts/assistant_cli.py --test
```

## Тестирование

Файл сценариев: [`test_questions.md`](test_questions.md) (23 вопроса: ORG, PII, MED, RESULTS, OTHER).

```bash
python scripts/assistant_cli.py --test
```

Создаются два файла в корне проекта (не в git):

| Файл | Содержимое |
|------|------------|
| `test_log_YYYYMMDD.txt` | Вопросы, найденные чанки (лучший помечен), черновик, ответ |
| `test_result_YYYYMMDD.txt` | AI-анализ лога: PASS/PARTIAL/FAIL, статистика |

Дополнительные опции:

```bash
python scripts/assistant_cli.py --test --test-file path/to/questions.md
python scripts/assistant_cli.py --skip-index-check   # без автоиндексации
```

## Переменные окружения

Полный список — в [`.env.example`](.env.example).

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OPENAI_API_KEY` | — | Ключ OpenAI (обязателен) |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель эмбеддингов |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Модель для ответов и классификатора |
| `LLM_TEMPERATURE` | `0.2` | Temperature генерации |
| `RAG_TOP_K` | `4` | Число чанков в контексте |
| `RAG_FETCH_K` | `12` | Кандидатов до rerank |
| `RAG_MAX_DISTANCE` | `1.25` | Порог distance (ниже — релевантнее) |
| `RAG_FOLDER_BOOST` | `0.12` | Буст по папке source |
| `RAG_CONTENT_BOOST` | `0.15` | Буст при совпадении слов в чанке |
| `ENABLE_QUALITY_CHECK` | `true` | LLM post-check после программной проверки |
| `EMBEDDING_PROVIDER` | `openai` | `openai` или `huggingface` |
| `TELEGRAM_BOT_TOKEN` | — | Зарезервировано для будущего бота |

## Ограничения (по ТЗ)

- Не ставит диагнозы, не назначает лечение, не интерпретирует анализы
- Не обрабатывает персональные данные в чате (ФИО, адрес, телефон, email)
- Отвечает только по документам из `source/` после индексации
- При отсутствии данных или сбое проверки — перевод на оператора

## Дальнейшие шаги

- [ ] Telegram-бот
- [ ] FastAPI backend
- [ ] Автоматические assert'ы по `test_questions.md` (сейчас — ручная / AI-оценка)

## Ссылки

- Репозиторий: https://github.com/DimonRonD/InMyHeart.git
