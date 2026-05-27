# Docker — развёртывание INMYHEART

Руководство по запуску AI-ассистента в **Docker Compose**: три сервиса на одном образе (`index` → `api` → `bot`).

---

## 1. Архитектура

```
                    ┌──────────────────────────────────────┐
                    │         docker compose               │
                    │                                      │
                    │  index (one-shot)                    │
                    │    индексация source/ → Chroma       │
                    │    restart: no                       │
                    │           │                          │
                    │           ▼                          │
  HTTP :8000 ──────►│  api (FastAPI)                       │
                    │    /health, /ask                       │
                    │    только читает готовый Chroma        │
                    │           │                          │
                    │           ▼                          │
  Telegram ────────►│  bot (polling)                       │
                    │    Forum Topics, relay, эскалация    │
                    │    depends_on: api (healthy)         │
                    │                                      │
                    └──────────────┬───────────────────────┘
                                   │
                          bind mount: ./data
                          ├── chroma/           ← RAG-индекс
                          ├── inmyheart.db      ← SQLite (WAL)
                          └── telegram_client_topics.json
```

| Сервис | Команда | Порт | Назначение |
|--------|---------|------|------------|
| **index** | `python scripts/index_knowledge_base.py --reset` | — | Однократная индексация при `up` |
| **api** | `python scripts/run_api.py` | `8000` | REST API, проверка готовности индекса |
| **bot** | `python scripts/telegram_bot.py` | — | Telegram-бот (long polling) |

**Почему три сервиса:** индексация Chroma — тяжёлая операция с записью SQLite. Если делать её в startup `api`, контейнер падает в restart loop при ошибках прав/диска (`readonly database`, code 1032). Отдельный `index` завершается один раз; `api` и `bot` только используют готовый `./data/chroma`.

**Почему bind mount `./data`, а не named volume:** на VPS проще выставить права на каталог хоста (`chmod -R 777 data`) и сбросить битый индекс без `docker volume rm`.

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
docker compose logs index
docker compose logs -f api bot
curl http://localhost:8000/health
```

Ожидаемый ответ `/health`:

```json
{"status": "ok", "indexed_chunks": 242}
```

Первый запуск может занять **2–5 минут** (сборка образа + сервис `index`).

Порядок старта: **`index` (completed) → `api` (healthy) → `bot`**.

---

## 4. Файлы

| Файл | Назначение |
|------|------------|
| [`Dockerfile`](../Dockerfile) | Образ Python 3.12, зависимости, код, `source/` |
| [`docker-compose.yml`](../docker-compose.yml) | Сервисы `index`, `api`, `bot`, bind mount `./data` |
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

Каталог **`./data`** на хосте монтируется в `/app/data` всех сервисов:

| Путь | Содержимое |
|------|------------|
| `data/chroma/` | Векторный индекс ChromaDB |
| `data/inmyheart.db` | Логи диалогов, KPI, сессии оператора |
| `data/telegram_client_topics.json` | Связь user_id → Forum Topic |

Перед первым запуском на сервере:

```bash
mkdir -p data/chroma
chmod -R 777 data
```

SQLite работает в режиме **WAL** (`bot/db.py`) для одновременной записи из `api` и `bot`.

**Бэкап:**

```bash
tar czf inmyheart-data-backup.tar.gz -C data .
# или из контейнера:
docker compose exec api tar czf - /app/data > inmyheart-data-backup.tar.gz
```

**Полный сброс данных INMYHEART** (не затрагивает другие Docker-проекты):

```bash
docker compose down
rm -rf data/chroma/* data/inmyheart.db data/telegram_client_topics.json
mkdir -p data/chroma && chmod -R 777 data
docker compose up --build -d
```

---

## 7. Переиндексация базы знаний

После изменения файлов в `source/` (в образе — нужна **пересборка**):

```bash
docker compose up --build -d
# или только переиндексация без пересборки api/bot:
docker compose run --rm index
docker compose restart api bot
```

Сервис `index` по умолчанию запускается с `--reset` (полная переиндексация).

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
# Сброс данных Chroma/SQLite — см. §6 (rm -rf data/chroma/* ...)

# НЕ используйте на сервере с другими проектами:
# docker system prune -a --volumes
# docker image prune -a

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
2. `indexed_chunks > 0` (индекс создан сервисом `index`)

Индексация **не** выполняется в `api` — только проверка. Параметры healthcheck: `start_period: 60s`, до 8 повторов.

Сервис `bot` не имеет HTTP healthcheck; стартует после `api: service_healthy`.

При сбое смотрите логи однократного job: `docker compose logs index`.

---

## 10. Продакшен на Debian (`/opt/inmyheart`)

Пошаговая установка на чистый **Debian 11/12** (VPS). Приложение работает через **Docker Compose** — Python на сервере ставить не нужно.

### 10.1. Подключитесь к серверу по SSH

```bash
ssh root@ВАШ_IP
# или: ssh user@ВАШ_IP && sudo -i
```

### 10.2. Автоматический деплой (рекомендуется)

```bash
apt-get update && apt-get install -y git
git clone https://github.com/DimonRonD/InMyHeart.git /opt/inmyheart
cd /opt/inmyheart
cp .env.example .env
nano .env   # OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_CHAT_ID
sudo bash scripts/deploy_debian.sh
```

Скрипт `scripts/deploy_debian.sh`:
- ставит Docker (если нет);
- клонирует/обновляет репозиторий в `/opt/inmyheart`;
- проверяет `.env`;
- выполняет `docker compose up --build -d`;
- ждёт `GET /health`.

### 10.3. Ручная установка (пошагово)

```bash
# 1. Пакеты
apt-get update
apt-get install -y git ca-certificates curl

# 2. Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker
docker compose version

# 3. Каталог и код
mkdir -p /opt/inmyheart
git clone https://github.com/DimonRonD/InMyHeart.git /opt/inmyheart
cd /opt/inmyheart

# 4. Секреты (не коммитьте .env!)
cp .env.example .env
nano .env
```

Минимум в `.env`:

```env
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_OPERATOR_CHAT_ID=-100...
TELEGRAM_HANDOFF_MODE=relay
TELEGRAM_USE_FORUM_TOPICS=true
```

```bash
# 5. Запуск
cd /opt/inmyheart
docker compose up --build -d

# 6. Проверка (первая индексация — 2–5 мин)
docker compose ps
docker compose logs -f api
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ: `{"status":"ok","indexed_chunks":242}` (число может отличаться).

### 10.4. Firewall и доступ

```bash
# ufw (если используется)
ufw allow OpenSSH
ufw allow 8000/tcp    # только если API нужен снаружи
ufw enable
```

Telegram-бот работает через **long polling** — входящий порт для бота не нужен.  
Порт **8000** открывайте только если нужен внешний доступ к `/ask` (лучше через nginx + HTTPS).

### 10.5. Автозапуск

`docker compose` с `restart: unless-stopped` в `docker-compose.yml` — контейнеры поднимаются после перезагрузки VPS, если Docker запущен:

```bash
systemctl is-enabled docker   # enabled
```

### 10.6. Обновление версии

```bash
cd /opt/inmyheart
git pull
docker compose up --build -d
```

### 10.7. Другие VPS

Те же шаги подходят для Hetzner, Timeweb, Yandex Cloud. Стоимость — [`costs.md`](costs.md) (~$35/мес).

---

## 11. Устранение неполадок

| Симптом | Решение |
|---------|---------|
| `bot` не стартует, ждёт `api` | `docker compose logs index` и `docker compose logs api` |
| `indexed_chunks: 0` | `docker compose run --rm index` |
| `TELEGRAM_BOT_TOKEN не задан` | Заполните `.env`, `docker compose up -d --force-recreate bot` |
| Forum Topics → #General | В BotFather включите **Manage Topics** для бота в группе операторов |
| `Conflict: terminated by other getUpdates` | Один экземпляр бота: `docker compose down`, убить локальный `telegram_bot.py` |
| База SQLite locked | Убедитесь, что WAL включён; не запускайте второй локальный процесс на том же `data/` |
| **`No space left on device` при сборке** | Диск VPS переполнен. См. §11.1 |
| **`readonly database` (Chroma 1032)** | Повреждён volume или права. См. §11.2 |

### 11.1. Мало места на диске (VPS 10 GB)

Сборка **полного** `requirements.txt` (torch + sentence-transformers) требует **6–8 GB** свободного места.  
Docker-образ использует **`requirements-docker.txt`** (только OpenAI embeddings) — **~1–2 GB** при сборке.

**Очистка места (безопасно для других Docker-проектов):**

```bash
cd /opt/inmyheart
docker compose down
docker builder prune -f
apt-get clean && apt-get autoremove -y
journalctl --vacuum-size=100M
df -h /
```

**Не запускайте на shared-сервере:** `docker system prune -a`, `docker image prune -a`, `docker volume prune` — затронут чужие образы/volumes.

**Минимум перед `docker compose up --build`:** ~**3 GB** свободно на `/`.

В `.env` обязательно: `EMBEDDING_PROVIDER=openai` (по умолчанию).

### 11.2. Chroma: `readonly database` (code 1032)

Обычно после неудачной индексации (диск был полон) каталог `data/chroma/` содержит **битые** файлы Chroma или каталог `./data` на хосте недоступен для записи.

**Только INMYHEART** — другие проекты не затрагиваются:

```bash
cd /opt/inmyheart
docker compose down
# старый named volume (если остался от прежней версии compose):
docker volume rm inmyheart_inmyheart-data 2>/dev/null || true
rm -rf data/chroma/*
mkdir -p data/chroma
chmod -R 777 data
git pull
docker compose up --build -d
docker compose logs index
docker compose logs api
```

Если не хотите удалять SQLite — сброс только Chroma:

```bash
docker compose down
rm -rf data/chroma/*
mkdir -p data/chroma && chmod -R 777 data
docker compose up --build -d
```

---

## 13. Несколько проектов на одном сервере

INMYHEART **не должен** останавливать и удалять чужие контейнеры, если вы работаете **только из каталога проекта**.

### Что изолировано

| Ресурс | Имя INMYHEART | Чужие проекты |
|--------|---------------|---------------|
| Compose-проект | `inmyheart` | свои имена |
| Контейнеры | `inmyheart-index`, `inmyheart-api`, `inmyheart-bot` | не трогаются |
| Данные | `./data` (bind mount) | не трогается |
| Образ | `inmyheart-assistant:latest` | не трогается |
| Сеть | `inmyheart_default` | отдельная |

### Безопасные команды (только INMYHEART)

Всегда сначала: `cd /opt/inmyheart`

```bash
docker compose ps
docker compose up --build -d
docker compose down
docker compose logs -f index api bot
docker compose run --rm index
# сброс данных: rm -rf data/chroma/* (см. §6)
```

### Опасные команды (затронут другие проекты)

| Команда | Риск |
|---------|------|
| `docker system prune -a --volumes` | Удалит неиспользуемые образы/volumes **всех** проектов |
| `docker image prune -a` | Может удалить образы других сервисов |
| `docker stop $(docker ps -q)` | Остановит **все** контейнеры |
| `docker rm -f ...` без имён | Случайно удалить не тот контейнер |

### Конфликт порта 8000

Если порт занят другим проектом, в `.env`:

```env
API_PORT=8010
```

И в `docker-compose.yml` проброс `${API_PORT:-8000}:8000` подхватит новый порт.

Проверка: `ss -tlnp | grep 8000`

### Конфликт Telegram-бота

Один `TELEGRAM_BOT_TOKEN` — **только один** процесс polling (локально или на сервере). Другие проекты с тем же токеном дадут `Conflict`.

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
