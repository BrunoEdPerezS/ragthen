import sys
from pathlib import Path

_embedding_model = None
_log_tag = "[ragthen]"

INDEX_DIRNAME = ".index"


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def get_collection(index_dir: Path):
    import chromadb
    client = chromadb.PersistentClient(path=str(index_dir))
    return client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})


def extract_pdf_pages(filepath: Path) -> list[dict]:
    import fitz
    doc = fitz.open(str(filepath))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({"text": text, "page": i + 1, "source": filepath.name})
    doc.close()
    return pages


def extract_text_file(filepath: Path) -> list[dict]:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    return [{"text": text, "page": 1, "source": filepath.name}]


def chunk_pages(pages: list[dict], chunk_size: int = 1200,
                chunk_overlap: int = 250) -> list[dict]:
    chunks = []
    stride = max(chunk_size - chunk_overlap, 1)
    for page in pages:
        text = page["text"]
        source = page["source"]
        page_num = page["page"]
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"text": chunk_text, "source": source, "page": page_num})
            if end == len(text):
                break
            start += stride
    return chunks
