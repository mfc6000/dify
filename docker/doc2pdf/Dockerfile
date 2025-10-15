FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# （可选）如果在国内网络，先切换国内源，避免 404/Timeout
# RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libreoffice \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        fontconfig \
        curl \
        tini \
        locales; \
    rm -rf /var/lib/apt/lists/*

# 中文 locale（可选）
RUN sed -i 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8

# Python 依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 非 root
RUN useradd -m appuser
USER appuser
WORKDIR /app

# 应用代码
COPY app /app

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--timeout-keep-alive","30"]
