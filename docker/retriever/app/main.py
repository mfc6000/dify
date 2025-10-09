from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(..., description="User query string")
    top_k: int = Field(10, ge=1, le=50, description="Number of documents to retrieve")


class SearchResponse(BaseModel):
    message: str
    detail: Dict[str, Any] = Field(default_factory=dict)


def create_app() -> FastAPI:
    app = FastAPI(title="Retriever Service", version="0.1.0")

    @app.get("/healthz", response_model=dict)
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/search", response_model=SearchResponse)
    def search(_: SearchRequest) -> SearchResponse:
        logger.warning("/search endpoint not yet implemented")
        raise HTTPException(status_code=501, detail="Retriever logic not implemented")

    return app


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "info").upper()
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main() -> None:
    configure_logging()
    app = create_app()
    port = int(os.getenv("PORT", "7001"))

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
