#!/bin/sh
set -e
# Volume /app/data должен быть доступен для записи (Chroma + SQLite).
mkdir -p /app/data/chroma
chmod -R u+rwX,g+rwX /app/data 2>/dev/null || true
exec "$@"
