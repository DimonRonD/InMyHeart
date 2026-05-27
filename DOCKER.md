# Docker — развёртывание INMYHEART

Руководство по запуску AI-ассистента в **Docker Compose**: два контейнера на одном образе (`api` + `bot`).

---

## 1. Архитектура

```
                    ┌──────────────────────────────────────┐
                    │         docker compose               │
                    │                                      │
  HTTP :8000 ──────►│  api (FastAPI)                       │
                    │    /health, /ask                     │
                    │    индексация Chroma при 1-м старте  │
                    │                                      │
  Telegram ────────►│  bot (polling)                       │
                    │    Forum Topics, relay, эскалация    │
                    │    depends_on: api (healthy)         │
                    │                                      │
                    └──────────────┬───────────────────────┘
                                   │
                          volume: inmyheart-data
                          ├── chroma/           ← RAG-индекс
                          ├── inmyheart.db      ← SQLite (WAL)
                          └── telegram_client_topics.json
```

| Сервис | Команда | Порт | Назначение |
|--------|---------|------|------------|
| **api** | `python scripts/run_api.py` | `8000` | REST API, первичная индексация |
| **bot** | `python scripts/telegram_bot.py` | — | Telegram-бот (long polling) |

**Почему два контейнера, а не один:** API и бот — разные процессы с разным lifecycle (HTTP-сервер vs polling). Общий образ и volume дают один Chroma и одну SQLite без дублирования кода.

**Почему не нужен третий контейнер (indexer):** индексация встроена в startup `api` (`ensure_index()`). `bot` стартует только после healthcheck API (`indexed_chunks > 0`).

---

## 2. Требования

- Docker Engine 24+ и Docker Compose v2
- Файл `.env` в корне проекта (см. [`.env.example`](../.env.example))
- Обязательно: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`
- Для операторов: `TELEGRAM_OPERATOR_CHAT_ID`, `TELEGRAM_HANDOFF_MODE=relay`

---

## 3. Быстрый старт

```bash
cp .env.example .env
# заполните OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_CHAT_ID

docker compose up --build -d
docker compose ps
docker compose logs -f api bot
curl http://localhost:8000/health
```

Ожидаемый ответ `/health`:

```json
{"status": "ok", "indexed_chunks": 242}
```

Первый запуск может занять **2–5 минут** (сборка образа + индексация `source/`).

---

## 4. Файлы

| Файл | Назначение |
|------|------------|
| [`Dockerfile`](../Dockerfile) | Образ Python 3.12, зависимости, код, `source/` |
| [`docker-compose.yml`](../docker-compose.yml) | Сервисы `api`, `bot`, volume, healthcheck |
| [`.dockerignore`](../.dockerignore) | Исключения при сборке (venv, `.env`, локальный `data/`) |

---

## 5. Переменные окружения в Docker

Compose **переопределяет** пути для контейнера:

| Переменная | В контейнере | Локально (без Docker) |
|------------|--------------|------------------------|
| `API_HOST` | `0.0.0.0` | `127.0.0.1` |
| `SOURCE_DIR` | `/app/source` | `./source` |
| `CHROMA_PERSIST_DIR` | `/app/data/chroma` | `./data/chroma` |
| `DIALOG_DB_PATH` | `/app/data/inmyheart.db` | `./data/inmyheart.db` |

Остальные переменные читаются из `.env` через `env_file`.

---

## 6. Персистентность данных

Volume **`inmyheart-data`** монтируется в `/app/data` обоих контейнеров:

| Путь в volume | Содержимое |
|---------------|------------|
| `chroma/` | Векторный индекс ChromaDB |
| `inmyheart.db` | Логи диалогов, KPI, сессии оператора |
| `telegram_client_topics.json` | Связь user_id → Forum Topic |

SQLite работает в режиме **WAL** (`bot/db.py`) для одновременной записи из `api` и `bot`.

**Бэкап:**

```bash
docker compose exec api tar czf - /app/data > inmyheart-data-backup.tar.gz
```

---

## 7. Переиндексация базы знаний

После изменения файлов в `source/` (в образе — нужна **пересборка**):

```bash
docker compose up --build -d api
docker compose exec api python scripts/index_knowledge_base.py --reset
docker compose restart bot
```

Если меняете `source/` только локально без пересборки — смонтируйте каталог (опционально, для dev):

```yaml
# docker-compose.override.yml (не в git)
services:
  api:
    volumes:
      - ./source:/app/source:ro
  bot:
    volumes:
      - ./source:/app/source:ro
```

---

## 8. Полезные команды

```bash
# Статус и логи
docker compose ps
docker compose logs -f api
docker compose logs -f bot --tail 100

# Остановка / удаление
docker compose down
docker compose down -v          # + удалить volume (Chroma и SQLite!)

# Только API (без бота)
docker compose up -d api

# Тест /ask из хоста
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"До скольки работает клиника в среду?\", \"user_id\": 1}"

# CLI-тест внутри контейнера
docker compose exec api python scripts/assistant_cli.py -q "Сколько стоит УЗИ?"

# pytest (integration, нужен OPENAI_API_KEY)
docker compose exec api pytest tests/ -m integration -v
```

---

## 9. Healthcheck

Сервис `api` считается готовым, когда:

1. HTTP `GET /health` отвечает 200
2. `indexed_chunks > 0` (Chroma проиндексирован)

Параметры: `start_period: 180s`, до 12 повторов — учитывает первую индексацию.

Сервис `bot` не имеет HTTP healthcheck; стартует после `api: service_healthy`.

---

## 10. Продакшен на VPS

1. Установить Docker на VPS (Hetzner, Timeweb, Yandex Cloud).
2. Клонировать репозиторий, создать `.env`.
3. `docker compose up --build -d`
4. Открыть порт **8000** (или прокси nginx → `/ask` для будущего веб-чата).
5. Telegram: polling работает без белого IP; webhook — отдельная доработка.
6. Мониторинг: внешний ping `GET /health`, алерт при падении контейнера.

Стоимость VPS заложена в [`costs.md`](../costs.md) (~$35/мес).

---

## 11. Устранение неполадок

| Симптом | Решение |
|---------|---------|
| `bot` не стартует, ждёт `api` | `docker compose logs api` — дождитесь индексации или проверьте `OPENAI_API_KEY` |
| `indexed_chunks: 0` | `docker compose exec api python scripts/index_knowledge_base.py --reset` |
| `TELEGRAM_BOT_TOKEN не задан` | Заполните `.env`, `docker compose up -d --force-recreate bot` |
| Forum Topics → #General | В BotFather включите **Manage Topics** для бота в группе операторов |
| `Conflict: terminated by other getUpdates` | Один экземпляр бота: `docker compose down`, убить локальный `telegram_bot.py` |
| База SQLite locked | Убедитесь, что WAL включён; не запускайте второй локальный процесс на том же `data/` |

---

## 12. Связанные документы

| Документ | Раздел |
|----------|--------|
| [`README.md`](../README.md) | Быстрый старт |
| [`stek.md`](../stek.md) | Стек и DevOps |
| [`operator_handoff.md`](../operator_handoff.md) | Telegram-операторы в контейнере |
| [`TZ_STATUS.md`](../TZ_STATUS.md) | Статус Docker vs ТЗ |
| [`test_questions.md`](../test_questions.md) | Тесты через Docker |
| [`costs.md`](../costs.md) | Бюджет VPS + OpenAI |

---

*INMYHEART · Docker Compose · 2026*
