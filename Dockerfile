# Multi-stage build for FinePrint: Legal AI Assistant

# Stage 1: Build Frontend Assets
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Static Serving
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    MOCK_LLM=1 \
    TESSERACT_CMD=tesseract

WORKDIR /app

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend, data, and fixtures
COPY backend/ ./backend/
COPY data/ ./data/
COPY fixtures/ ./fixtures/

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
