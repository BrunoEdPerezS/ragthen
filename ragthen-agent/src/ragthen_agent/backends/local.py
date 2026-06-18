from .interface import Backend
from ragthen_core.engine import (ingest as _ingest, search as _search, ask as _ask,
                                     status as _status, clear as _clear, list_libraries as _list,
                                     resolve_library)
from ragthen_core.config import load_config


class LocalBackend(Backend):
    """Uses ragthen-core directly as a Python library. Zero network calls."""

    def ingest(self, library: str) -> None:
        lib_dir, index_dir = resolve_library(library)
        _ingest(lib_dir, index_dir)

    def search(self, query: str, library: str, top_k: int = 5,
               relevance_threshold: float = 0.0, rerank: bool = False) -> list[dict]:
        _, index_dir = resolve_library(library)
        return _search(query, index_dir, top_k=top_k,
                       relevance_threshold=relevance_threshold, rerank=rerank)

    def ask(self, query: str, library: str,
            api_key: str | None = None, model: str = "gpt-4o") -> str:
        _, index_dir = resolve_library(library)
        cfg = load_config()
        model = model or cfg.get("llm_model", "gpt-4o")
        return _ask(query, index_dir, library, api_key=api_key, model_name=model)

    def status(self, library: str) -> None:
        _, index_dir = resolve_library(library)
        _status(index_dir, library)

    def clear(self, library: str) -> None:
        _, index_dir = resolve_library(library)
        _clear(index_dir, library)

    def list_libraries(self) -> None:
        _list()
