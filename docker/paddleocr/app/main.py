from __future__ import annotations

import base64
import binascii
import os
import pathlib
import secrets
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

# 可选：将本地目录以静态路由暴露（便于生成 image_url）
# 若不需要对外暴露静态URL，可忽略这段环境变量配置。
STATIC_MOUNT_DIR = os.getenv("STATIC_MOUNT_DIR")           # 例如: "/tmp/ocr_uploads"
STATIC_URL_PREFIX = os.getenv("STATIC_URL_PREFIX", "/uploads")  # 例如: "/ocr_pages"

try:
    from paddleocr import PaddleOCR
except ImportError as exc:  # pragma: no cover - import guard for runtime image
    raise RuntimeError("paddleocr must be installed inside the container") from exc


# ========= 数据模型 =========

class OCRRequest(BaseModel):
    image_url: Optional[HttpUrl] = None
    image_base64: Optional[str] = None
    local_file: Optional[str] = None         # ✅ 新增：容器内部文件路径
    detect_angle: bool = True


class OCRResponse(BaseModel):
    text: str
    boxes: List[List[List[float]]]
    lines: List[Dict[str, Any]]


class UploadResponse(BaseModel):
    path: str
    url: Optional[str] = None                # 如果配置了静态路由，则返回可访问 URL


# ========= 工具函数 =========

def _bytes_to_array(raw_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image bytes")
    return image


def _load_image_from_base64(image_base64: str) -> np.ndarray:
    try:
        decoded = base64.b64decode(image_base64)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc
    return _bytes_to_array(decoded)


def _load_image_from_url(image_url: str) -> np.ndarray:
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {exc}") from exc
    return _bytes_to_array(response.content)


def _load_image_from_local(path: str) -> np.ndarray:
    if not path:
        raise HTTPException(status_code=400, detail="local_file is empty")
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail=f"local_file not found: {path}")
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read local_file: {exc}") from exc
    return _bytes_to_array(data)


def _init_ocr() -> PaddleOCR:
    lang = os.getenv("PPOCR_LANG", "ch")
    version = os.getenv("PPOCR_MODEL_VERSION", "PP-OCRv4")
    use_gpu = os.getenv("PPOCR_USE_GPU", "false").lower() == "true"
    det_model_dir = os.getenv("PPOCR_DET_MODEL_DIR")
    rec_model_dir = os.getenv("PPOCR_REC_MODEL_DIR")
    cls_model_dir = os.getenv("PPOCR_CLS_MODEL_DIR")

    kwargs: Dict[str, Any] = {
        "use_angle_cls": True,
        "lang": lang,
        "ocr_version": version,
        "use_gpu": use_gpu,
    }

    if det_model_dir:
        kwargs["det_model_dir"] = det_model_dir
    if rec_model_dir:
        kwargs["rec_model_dir"] = rec_model_dir
    if cls_model_dir:
        kwargs["cls_model_dir"] = cls_model_dir

    return PaddleOCR(**kwargs)


# ========= 应用与可选静态挂载 =========

app = FastAPI(title="PP-OCRv4 slim service", version="0.2.0")
ocr_engine = _init_ocr()

# 如果配置了 STATIC_MOUNT_DIR，则将其挂载为静态路由，便于组成 image_url
if STATIC_MOUNT_DIR:
    from fastapi.staticfiles import StaticFiles
    os.makedirs(STATIC_MOUNT_DIR, exist_ok=True)
    app.mount(STATIC_URL_PREFIX, StaticFiles(directory=STATIC_MOUNT_DIR), name="uploads")


# ========= 健康检查 =========

@app.get("/healthz", response_model=dict)
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


# ========= 新增：上传图片，保存在容器临时目录 =========

@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """
    接收客户端上传的图片，将其保存到容器内目录（默认 /tmp/ocr_uploads 或 env STATIC_MOUNT_DIR）。
    返回:
      - path: 容器内部可读的文件路径（可用于随后调用 /ocr 时的 local_file）
      - url:  如果启用了静态挂载，返回可访问的 URL（STATIC_URL_PREFIX/<filename>）
    """
    # 1) 选择保存目录：优先 STATIC_MOUNT_DIR，其次 /tmp/ocr_uploads
    save_dir = STATIC_MOUNT_DIR or os.getenv("UPLOAD_DIR", "/tmp/ocr_uploads")
    os.makedirs(save_dir, exist_ok=True)

    # 2) 生成简洁的随机文件名，保留扩展名（若无扩展名则用 .png）
    orig_suffix = pathlib.Path(file.filename or "").suffix.lower()
    if orig_suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}:
        orig_suffix = ".png"
    filename = f"up_{secrets.token_hex(8)}{orig_suffix}"
    dest_path = os.path.join(save_dir, filename)

    # 3) 保存文件
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file")
        with open(dest_path, "wb") as f:
            f.write(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to save file: {exc}") from exc

    # 4) 组织响应
    url = None
    if STATIC_MOUNT_DIR:
        # 可通过服务内部 DNS 用 http://ocr:PORT 访问；对外可用你的网关/Nginx 域名
        url = f"{STATIC_URL_PREFIX.rstrip('/')}/{filename}"

    return UploadResponse(path=dest_path, url=url)


# ========= OCR 主接口：支持 local_file / image_url / image_base64 =========

@app.post("/ocr", response_model=OCRResponse)
def run_ocr(payload: OCRRequest) -> OCRResponse:
    """
    优先级：
      1) local_file    -> 从容器内部路径读取图片（配合 /upload）
      2) image_url     -> 从 URL 下载图片
      3) image_base64  -> 从 base64 解码
    三者至少提供其一。
    """
    if not (payload.local_file or payload.image_url or payload.image_base64):
        raise HTTPException(status_code=400, detail="One of local_file, image_url, or image_base64 is required")

    if payload.local_file:
        image = _load_image_from_local(payload.local_file)
    elif payload.image_url:
        image = _load_image_from_url(str(payload.image_url))
    else:
        assert payload.image_base64 is not None
        image = _load_image_from_base64(payload.image_base64)

    result = ocr_engine.ocr(image, cls=payload.detect_angle)

    lines: List[Dict[str, Any]] = []
    texts: List[str] = []
    boxes: List[List[List[float]]] = []

    for line in result:
        for box, (text, score) in line:
            boxes.append([[float(x), float(y)] for x, y in box])
            lines.append({"text": text, "score": float(score), "box": boxes[-1]})
            texts.append(text)

    joined_text = "\n".join(texts)

    return OCRResponse(text=joined_text, boxes=boxes, lines=lines)
