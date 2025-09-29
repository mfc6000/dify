FROM python:3.10-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/paddleocr/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/paddleocr/app ./app

ARG PPOCR_LANG=ch
ARG PPOCR_MODEL_VERSION=PP-OCRv4
ENV PPOCR_LANG=${PPOCR_LANG} \
    PPOCR_MODEL_VERSION=${PPOCR_MODEL_VERSION} \
    PPOCR_USE_GPU=false \
    SERVICE_PORT=8504

# Pre-download models so the container is ready at runtime
RUN python - <<'PY'
import os
from paddleocr import PaddleOCR

PaddleOCR(
    use_angle_cls=True,
    lang=os.getenv("PPOCR_LANG", "ch"),
    ocr_version=os.getenv("PPOCR_MODEL_VERSION", "PP-OCRv4"),
    use_gpu=False,
)
PY

EXPOSE 8504

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8504}"]
