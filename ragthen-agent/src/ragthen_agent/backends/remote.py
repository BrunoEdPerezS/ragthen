import json
import sys
import urllib.request
import urllib.error
from .interface import Backend
from ragthen_core.config import load_config

_log_tag = "[ragthen]"


class RemoteBackend(Backend):
    """Talks to a Ragthen API server via HTTP. No local ChromaDB needed."""

    def __init__(self, base_url: str | None = None):
        cfg = load_config()
        self.base_url = (base_url or cfg.get("remote_url", "http://localhost:8000")).rstrip("/")

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"{_log_tag} API error {e.code}: {body}", file=sys.stderr)
            return {}
        except Exception as e:
            print(f"{_log_tag} Connection error: {e}", file=sys.stderr)
            return {}

    def ingest(self, library: str,
               pdfparser_mode: str | None = None,
               chunking_strategy: str | None = None) -> None:
        payload = {"library": library}
        if pdfparser_mode:
            payload["pdfparser"] = pdfparser_mode
        if chunking_strategy:
            payload["chunking"] = chunking_strategy
        self._post("/ingest", payload)

    def search(self, query: str, library: str, top_k: int = 5,
               relevance_threshold: float = 0.0, rerank: bool = False,
               reranker_type: str | None = None) -> list[dict]:
        payload = {
            "query": query, "library": library, "top_k": top_k,
            "relevance_threshold": relevance_threshold, "rerank": rerank,
        }
        if reranker_type:
            payload["reranker"] = reranker_type
        result = self._post("/search", payload)
        return result.get("results", [])

    def ask(self, query: str, library: str,
            api_key: str | None = None, model: str = "gpt-4o") -> str:
        result = self._post("/ask", {
            "query": query, "library": library,
            "api_key": api_key, "model": model,
        })
        return result.get("answer", "")

    def status(self, library: str) -> None:
        result = self._post("/status", {"library": library})
        print(result.get("message", ""))

    def clear(self, library: str) -> None:
        result = self._post("/clear", {"library": library})
        print(result.get("message", ""))

    def list_libraries(self) -> None:
        result = self._post("/libraries", {})
        print(result.get("message", ""))
