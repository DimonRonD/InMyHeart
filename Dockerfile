FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY api/ api/
COPY bot/ bot/
COPY rag/ rag/
COPY scripts/ scripts/
COPY source/ source/
COPY prompts.md chunck_splitting.md ./

RUN mkdir -p /app/data/chroma

# api | bot — задаётся в docker-compose.yml
# Документация: DOCKER.md
CMD ["python", "scripts/run_api.py"]
