#!/bin/sh
set -e

mkdir -p /app/data/chroma
chmod -R 777 /app/data 2>/dev/null || true

if ! touch /app/data/.write_test 2>/dev/null; then
  echo "FATAL: /app/data is not writable" >&2
  ls -la /app/data >&2 || true
  exit 1
fi
rm -f /app/data/.write_test

exec "$@"
