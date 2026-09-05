FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY project-hub/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY project-hub/backend/app ./app
COPY project-hub/backend/alembic ./alembic
COPY project-hub/backend/alembic.ini ./

ENV UPLOAD_DIR=/app/uploads
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "100", "--timeout-keep-alive", "30"]
