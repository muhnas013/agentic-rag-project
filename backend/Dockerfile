# Python 3.12 dipakai karena host hanya menyediakan 3.14, sedangkan
# paddlepaddle (dependency PaddleOCR, Fase 5) belum merilis wheel untuk
# versi itu. Lihat docs/tech-decisions.md keputusan D-01.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libmagic1 dibutuhkan python-magic untuk memeriksa MIME type file upload.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency disalin lebih dulu agar layer-nya ikut cache saat kode berubah.
COPY requirements.txt /app/backend/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/backend/requirements.txt

COPY . /app/backend

# Dijalankan sebagai user biasa, bukan root.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/storage/uploads /app/storage/processed \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# --reload berguna karena ./backend di-mount sebagai volume saat pengembangan.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
