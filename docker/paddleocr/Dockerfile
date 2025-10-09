# ---- Base ----
FROM python:3.10-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# 基础依赖：含 OpenCV/NumPy 运行所需的 X/GL/OMP 库与 curl
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        libgomp1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先安装依赖（能命中 pip 缓存层）
COPY docker/paddleocr/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY docker/paddleocr/app ./app

# ---- Runtime env ----
ARG PPOCR_LANG=ch
ARG PPOCR_MODEL_VERSION=PP-OCRv4
ENV PPOCR_LANG=${PPOCR_LANG} \
    PPOCR_MODEL_VERSION=${PPOCR_MODEL_VERSION} \
    PPOCR_USE_GPU=false \
    SERVICE_PORT=8504 \
    # PaddleOCR 默认的模型缓存根目录（与 PaddleOCR 的轮子保持一致）
    OCR_HOME=/root/.paddleocr/whl

# ---- 预下载模型（手动下载，避免运行 PaddleOCR 时的核心转储） ----
RUN set -eux; \
    mkdir -p ${OCR_HOME}/det/ch \
             ${OCR_HOME}/rec/ch \
             ${OCR_HOME}/cls/ch; \
    # det
    curl -fL --retry 3 -o /tmp/det.tar \
      https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar; \
    tar -xf /tmp/det.tar -C ${OCR_HOME}/det/ch; \
    # rec
    curl -fL --retry 3 -o /tmp/rec.tar \
      https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar; \
    tar -xf /tmp/rec.tar -C ${OCR_HOME}/rec/ch; \
    # cls
    # 分类模型仍沿用官方发布的最新版本（同 PP-OCRv3）
    curl -fL --retry 3 -o /tmp/cls.tar \
      https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar; \
    tar -xf /tmp/cls.tar -C ${OCR_HOME}/cls/ch; \
    # 清理
    rm -f /tmp/*.tar

EXPOSE 8504

# 运行服务（按你的入口保持）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-8504}"]
