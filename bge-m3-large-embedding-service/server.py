
import os
import base64
from typing import List, Union, Optional, Dict, Any
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import torch
from FlagEmbedding import BGEM3FlagModel

API_KEY = os.getenv("API_KEY", "").strip()
MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-m3-large")
DEVICE_ENV = os.getenv("DEVICE", "auto").lower()
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
RETURN_SPARSE = os.getenv("RETURN_SPARSE", "false").lower() == "true"

def get_device():
    if DEVICE_ENV == "cpu":
        return "cpu"
    if DEVICE_ENV == "cuda":
        return "cuda" if torch.cuda.is_available() else "cpu"
    # auto
    return "cuda" if torch.cuda.is_available() else "cpu"

DEVICE = get_device()

# Load model once at startup
flag_model = BGEM3FlagModel(
    MODEL_NAME,
    use_fp16=(DEVICE == "cuda"),
    device=DEVICE
)

app = FastAPI(title="bge-m3-large Embedding Service", version="1.0.0")

class EmbeddingsRequest(BaseModel):
    model: Optional[str] = Field(default=MODEL_NAME)
    input: Union[str, List[str]]
    encoding_format: Optional[str] = Field(default="float")  # "float" or "base64"

class EmbeddingDatum(BaseModel):
    object: str = "embedding"
    index: int
    embedding: Union[List[float], str]

class EmbeddingsResponse(BaseModel):
    data: List[EmbeddingDatum]
    model: str
    object: str = "list"
    usage: Dict[str, int] = {"prompt_tokens": 0, "total_tokens": 0}

def _ensure_auth(authorization: Optional[str]):
    if not API_KEY:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/healthz")
def healthz():
    return {"status": "ok", "device": DEVICE, "model": MODEL_NAME}

@app.post("/v1/embeddings", response_model=EmbeddingsResponse)
def embeddings(req: EmbeddingsRequest, authorization: Optional[str] = Header(default=None)):
    _ensure_auth(authorization)

    texts = req.input if isinstance(req.input, list) else [req.input]
    # Truncate long texts to MAX_LENGTH tokens implicitly handled by model.encode(max_length=...)
    outs = flag_model.encode(
        texts,
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
        return_dense=True,
        return_sparse=RETURN_SPARSE,
        return_colbert_vecs=False
    )
    dense = outs["dense_vecs"]

    data = []
    for i, vec in enumerate(dense):
        if req.encoding_format == "base64":
            b = base64.b64encode(vec.tobytes()).decode("utf-8")
            data.append(EmbeddingDatum(index=i, embedding=b))
        else:
            data.append(EmbeddingDatum(index=i, embedding=vec.tolist()))

    return EmbeddingsResponse(data=data, model=req.model or MODEL_NAME)
