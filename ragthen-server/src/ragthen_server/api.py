"""Ragthen FastAPI server — exposes RAG capabilities as REST API."""
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from ragthen_core.engine import (ingest as _ingest, search as _search,
                                     ask as _ask, status as _status,
                                     clear as _clear, list_libraries as _list,
                                     resolve_library)
from ragthen_core.config import load_config

app = FastAPI(title="Ragthen API", version="0.1.0")

_API_KEY = os.environ.get("RAGTHEN_API_KEY", "")


def _verify_key(key: str | None):
    if not _API_KEY:
        return
    if not key or key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class IngestRequest(BaseModel):
    library: str
    pdfparser: str = "auto"
    chunking: str = "sentence"


class SearchRequest(BaseModel):
    library: str
    query: str
    top_k: int = 10
    relevance_threshold: float = 0.0
    rerank: bool = True
    reranker: str = "cross-encoder"


class AskRequest(BaseModel):
    library: str
    query: str
    api_key: str = ""
    model: str = "gpt-4o"


class StatusRequest(BaseModel):
    library: str


class ClearRequest(BaseModel):
    library: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(req: IngestRequest,
           x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        lib_dir, index_dir = resolve_library(req.library)
        _ingest(lib_dir, index_dir,
                pdfparser_mode=req.pdfparser,
                chunking_strategy=req.chunking)
        return {"status": "ok", "library": req.library}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search(req: SearchRequest,
           x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        _, index_dir = resolve_library(req.library)
        results = _search(req.query, index_dir, top_k=req.top_k,
                          relevance_threshold=req.relevance_threshold,
                          rerank=req.rerank, reranker_type=req.reranker)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask(req: AskRequest,
        x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        _, index_dir = resolve_library(req.library)
        key = req.api_key or os.environ.get("OPENAI_API_KEY")
        answer = _ask(req.query, index_dir, req.library,
                      api_key=key, model_name=req.model)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/status")
def status(req: StatusRequest,
           x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        _, index_dir = resolve_library(req.library)
        _status(index_dir, req.library)
        return {"status": "ok", "library": req.library}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
def clear(req: ClearRequest,
          x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        _, index_dir = resolve_library(req.library)
        _clear(index_dir, req.library)
        return {"status": "ok", "library": req.library}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/libraries")
def libraries(x_api_key: str | None = Header(None)):
    _verify_key(x_api_key)
    try:
        _list()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
