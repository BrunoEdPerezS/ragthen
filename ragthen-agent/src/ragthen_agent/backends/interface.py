from abc import ABC, abstractmethod


class Backend(ABC):

    @abstractmethod
    def ingest(self, library: str,
               pdfparser_mode: str | None = None,
               chunking_strategy: str | None = None) -> None:
        ...

    @abstractmethod
    def search(self, query: str, library: str, top_k: int = 5,
               relevance_threshold: float = 0.0, rerank: bool = False,
               reranker_type: str | None = None) -> list[dict]:
        ...

    @abstractmethod
    def ask(self, query: str, library: str,
            api_key: str | None = None, model: str = "gpt-4o") -> str:
        ...

    @abstractmethod
    def status(self, library: str) -> None:
        ...

    @abstractmethod
    def clear(self, library: str) -> None:
        ...

    @abstractmethod
    def list_libraries(self) -> None:
        ...
