from __future__ import annotations

import base64
import binascii
import os
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

try:
    from paddleocr import PaddleOCR
except ImportError as exc:  # pragma: no cover - import guard for runtime image
    raise RuntimeError("paddleocr must be installed inside the container") from exc


class OCRRequest(BaseModel):
    image_url: Optional[HttpUrl] = None
    image_base64: Optional[str] = None
    detect_angle: bool = True


class OCRResponse(BaseModel):
    text: str
    boxes: List[List[List[float]]]
    lines: List[Dict[str, Any]]


def _load_image_from_base64(image_base64: str) -> np.ndarray:
    try:
        decoded = base64.b64decode(image_base64)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image data") from exc
    return _bytes_to_array(decoded)


def _bytes_to_array(raw_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image bytes")
    return image


def _load_image_from_url(image_url: str) -> np.ndarray:
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {exc}") from exc
    return _bytes_to_array(response.content)


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


app = FastAPI(title="PP-OCRv4 slim service", version="0.1.0")
ocr_engine = _init_ocr()


@app.get("/healthz", response_model=dict)
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/ocr", response_model=OCRResponse)
def run_ocr(payload: OCRRequest) -> OCRResponse:
    if not payload.image_url and not payload.image_base64:
        raise HTTPException(status_code=400, detail="Either image_url or image_base64 is required")

    if payload.image_url:
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
