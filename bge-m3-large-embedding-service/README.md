
# bge-m3-large Local Embedding Service (OpenAI-compatible)

A minimal, production-minded Embedding service that wraps **Hugging Face `BAAI/bge-m3-large`** via **FlagEmbedding** and exposes an **OpenAI-compatible `/v1/embeddings`** endpoint.

Works on Linux/macOS/Windows/WSL; supports CPU and NVIDIA GPU. Includes Docker & docker-compose.

---

## 1) Quick Start (Python)

### 1.1 Create venv & install deps
```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -U pip
# CPU-only quick path:
pip install -r requirements.txt
# If you want GPU acceleration, first install a CUDA-matching torch from https://pytorch.org/get-started/locally/
# then re-run: pip install -r requirements.txt
```

### 1.2 Run the server
```bash
export MODEL_NAME="BAAI/bge-m3-large"   # can be a local path
export DEVICE="auto"                    # "auto" | "cuda" | "cpu"
export MAX_LENGTH=512
export BATCH_SIZE=32
export RETURN_SPARSE=false              # "true" to also compute lexical weights (slower)
uvicorn server:app --host 0.0.0.0 --port 8200
```

### 1.3 Test
```bash
curl -s http://localhost:8200/healthz

curl -s http://localhost:8200/v1/embeddings -H "Content-Type: application/json" -d '{
  "model": "bge-m3-large",
  "input": ["平台工程是什么？","What is Platform Engineering?"],
  "encoding_format": "float"           // optional, "float" (default) or "base64"
}'
```

Use with OpenAI SDK:
```python
from openai import OpenAI
client = OpenAI(api_key="EMPTY", base_url="http://localhost:8200/v1/")
resp = client.embeddings.create(model="bge-m3-large", input="什么是平台工程？")
print(len(resp.data[0].embedding))
```

---

## 2) Docker

### 2.1 CPU image
```bash
docker build -t bge-m3-large-embed:cpu .
docker run --rm -p 8200:8200 -e MODEL_NAME=BAAI/bge-m3-large bge-m3-large-embed:cpu
```

### 2.2 GPU image (requires nvidia-container-runtime)
Edit `docker/Dockerfile.gpu` if needed, then:
```bash
docker build -f docker/Dockerfile.gpu -t bge-m3-large-embed:gpu .
docker run --rm --gpus all -p 8200:8200 -e MODEL_NAME=BAAI/bge-m3-large bge-m3-large-embed:gpu
```

### 2.3 docker-compose
```bash
cp .env.example .env   # adjust as needed
docker compose up --build
# For GPU: uncomment the gpu service in docker-compose.yml and use: docker compose up --build embed-gpu
```

---

## 3) Weaviate Integration (manual vectors)

Use `examples/weaviate_setup.py`, `examples/ingest.py`, `examples/search_hybrid.py`.

1) Start Weaviate locally for a quick demo:
```bash
docker run -p 8080:8080 -e QUERY_DEFAULTS_LIMIT=25 semitechnologies/weaviate:latest
```

2) In another terminal:
```bash
python examples/weaviate_setup.py
python examples/ingest.py
python examples/search_hybrid.py
```

---

## 4) Notes & Tuning

- `MAX_LENGTH` (default 512): truncate long texts to keep latency stable.
- Batch with `BATCH_SIZE` for throughput; reduce if OOM.
- GPU: set `DEVICE=cuda` and ensure `torch.cuda.is_available()` is True.
- To switch model: set `MODEL_NAME` to `BAAI/bge-m3` (smaller) or a local path.
- `RETURN_SPARSE=true` will compute `lexical_weights` (sparse/keyword scores) for hybrid retrieval pipelines (slower).
- For high concurrency: run multiple workers (e.g., `uvicorn server:app --workers 2 --host 0.0.0.0 --port 8200`). Prefer 1 GPU per worker.

---

## 5) Security

- Put the service behind your API gateway; add simple API key if needed (see `API_KEY` env in `server.py`).
- For production, enable TLS and proper auth (API gateway/OIDC).

---

## 6) Files

- `server.py` — FastAPI OpenAI-compatible service
- `requirements.txt` — Python deps
- `docker/Dockerfile.cpu` — CPU image (slim)
- `docker/Dockerfile.gpu` — CUDA base image (runtime)
- `docker-compose.yml` — compose for CPU & GPU
- `examples/*` — Weaviate demo (create, ingest, search)

