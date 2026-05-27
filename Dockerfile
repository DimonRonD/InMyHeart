FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements-docker.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && pip install --upgrade pip \
    && pip install -r requirements-docker.txt \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY api/ api/
COPY bot/ bot/
COPY rag/ rag/
COPY scripts/ scripts/
COPY source/ source/
COPY prompts.md chunck_splitting.md ./
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /app/data/chroma \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]

# api | bot — задаётся в docker-compose.yml
# Документация: DOCKER.md
CMD ["python", "scripts/run_api.py"]
