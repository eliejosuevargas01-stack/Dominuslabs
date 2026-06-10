# --- Stage 1: Build the frontend ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Build the backend and assemble ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including pg client library just in case)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app ./app

# Copy built frontend assets to /app/static
COPY --from=frontend-builder /app/frontend/dist /app/static

ENV UPLOAD_DIR=/app/uploads
ENV PORT=8000

EXPOSE 8000

# Run uvicorn pointing to app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
