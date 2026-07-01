# LlamaIndex Migration — Proposal

## Why

Ragthen's current ingestion pipeline has serious quality issues with academic
PDFs — the primary format of the user's libraries. PyMuPDF's `page.get_text()`
produces:

- **Zero chunks** for scanned PDFs (no OCR)
- **Corrupted encoding** (accents become `?`)
- **Mixed layout** (tables, columns, TOC contaminating content)
- **Interleaved headers/footers** with body text

The chunking strategy is equally problematic: a blind 1200-character sliding
window that cuts words and sentences in half, with no semantic awareness.

The EPUB pipeline proved that with good extraction + semantic chunking the
system works well, but EPUBs are not available for the user's academic books.

## What Changes

Replace `ragthen-core`'s entire extraction, chunking, embedding, search, and
reranking pipeline with LlamaIndex — a mature RAG framework. The CLI, agent,
and backends adapt to use the new engine without changing their interface.

### New Capabilities

- **PDFPaddleOCR**: OCR-based extraction for scanned PDFs (local, free)
- **LlamaParse** (optional): cloud-based agentic PDF parser for maximum quality
- **SentenceSplitter**: token-based chunking that respects word/sentence boundaries
- **SemanticChunker**: embedding-based chunking that groups semantically related content
- **Configurable embeddings**: OpenAI, HuggingFace, Ollama — no longer locked to
  `all-MiniLM-L6-v2`
- **Configurable rerankers**: LLMRerank, SentenceTransformerRerank, CohereRerank
- **Metadata Extractors**: TitleExtractor, SummaryExtractor, KeywordExtractor
- **IngestionPipeline**: modular, cachable pipeline for processing

### New Package

- **ragthen-server**: FastAPI + MCP server for remote access (same name,
  new package in monorepo)

### Modified Capabilities

- **ragthen-core**: Entire engine replaced with LlamaIndex wrapper
- **ragthen-agent**: CLI adapted to use LlamaIndexEngine, agent prompt adjusted

### Impact

- New dependencies: `llama-index-core`, `llama-index-vector-stores-chroma`,
  `paddleocr` (optional `llama-index-readers-file`, `llama-parse`)
- Files removed: `ragthen-core/src/ragthen_core/storage.py`,
  `ragthen-core/src/ragthen_core/rerank.py`
- Files rewritten: `ragthen-core/src/ragthen_core/engine.py`,
  `ragthen-agent/src/ragthen_agent/cli.py`
- Files created: `ragthen-server/` package (new)
- No breaking changes to the CLI interface or the OpenCode agent
