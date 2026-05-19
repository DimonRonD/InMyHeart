# InMyHeart — AI-ассистент медицинской клиники

RAG-ассистент на базе LangChain и ChromaDB для ответов на организационные вопросы пациентов клиники INMYHEART.

## Структура

- `source/` — документы базы знаний (FAQ, услуги, расписание, памятки)
- `rag/` — чанкинг, эмбеддинги, индексация в Chroma
- `scripts/` — генерация документов, индексация, поиск
- `chunck_splitting.md` — правила разбиения на чанки
- `data/chroma/` — векторная БД (не в git)

## Быстрый старт

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Заполните OPENAI_API_KEY и TELEGRAM_BOT_TOKEN в .env

python scripts/index_knowledge_base.py --reset
python scripts/query_knowledge_base.py "как записаться к врачу" -k 3
```

## Переменные окружения

См. `.env.example`. Эмбеддинги по умолчанию: OpenAI `text-embedding-3-small`.
