#!/usr/bin/env bash
# Развёртывание INMYHEART на Debian в /opt/inmyheart (Docker Compose).
# Запуск на сервере: sudo bash scripts/deploy_debian.sh
set -euo pipefail

INSTALL_DIR="/opt/inmyheart"
REPO_URL="https://github.com/DimonRonD/InMyHeart.git"
COMPOSE="docker compose"

log() { echo "[deploy] $*"; }
die() { echo "[deploy] ERROR: $*" >&2; exit 1; }

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  die "Запустите от root: sudo bash $0"
fi

export DEBIAN_FRONTEND=noninteractive

log "Установка базовых пакетов..."
apt-get update -qq
apt-get install -y -qq git ca-certificates curl

if ! command -v docker >/dev/null 2>&1; then
  log "Docker не найден — установка через get.docker.com..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
else
  log "Docker уже установлен: $(docker --version)"
fi

if ! docker compose version >/dev/null 2>&1; then
  die "Нужен Docker Compose v2 (плагин docker compose). Переустановите Docker."
fi

mkdir -p "$INSTALL_DIR"

if [[ -d "$INSTALL_DIR/.git" ]]; then
  log "Обновление репозитория в $INSTALL_DIR..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  if [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]]; then
    die "$INSTALL_DIR не пуст и не git-репозиторий. Очистите каталог или выберите другой путь."
  fi
  log "Клонирование $REPO_URL -> $INSTALL_DIR..."
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  log "Создан .env из .env.example"
  log "ОБЯЗАТЕЛЬНО отредактируйте $INSTALL_DIR/.env:"
  log "  OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_OPERATOR_CHAT_ID"
  log "  TELEGRAM_HANDOFF_MODE=relay (если нужен relay оператора)"
  die "Заполните .env и снова выполните: sudo bash scripts/deploy_debian.sh"
fi

if grep -q 'sk-\.\.\.' .env || grep -q '123456789:ABC' .env; then
  die "В .env остались шаблонные значения. Отредактируйте $INSTALL_DIR/.env"
fi

log "Подготовка каталога данных (bind mount ./data)..."
mkdir -p "$INSTALL_DIR/data/chroma"
chmod -R 777 "$INSTALL_DIR/data"

log "Сборка и запуск контейнеров (index → api → bot)..."
$COMPOSE up --build -d

log "Проверка однократной индексации..."
if ! $COMPOSE logs index 2>/dev/null | grep -q "Индексация завершена"; then
  log "Сервис index ещё выполняется или завершился с ошибкой. Логи:"
  $COMPOSE logs --tail 80 index || true
fi

log "Ожидание healthcheck API (до ~3 мин)..."
for i in $(seq 1 36); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    curl -s "http://127.0.0.1:8000/health"
    echo
    break
  fi
  sleep 5
  if [[ "$i" -eq 36 ]]; then
    log "Healthcheck не прошёл за 3 мин. Смотрите логи:"
    $COMPOSE logs --tail 50 index
    $COMPOSE logs --tail 50 api
    exit 1
  fi
done

$COMPOSE ps

cat <<EOF

=== INMYHEART развёрнут в $INSTALL_DIR ===

Полезные команды:
  cd $INSTALL_DIR
  docker compose ps
  docker compose logs -f index api bot
  curl http://127.0.0.1:8000/health

Обновление после git push:
  cd $INSTALL_DIR && git pull && docker compose up --build -d

Документация: $INSTALL_DIR/DOCKER.md

EOF
