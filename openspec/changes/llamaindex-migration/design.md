# LlamaIndex Migration — Design

## Goals

1. Replace PDF extraction with OCR-capable reader (PDFPaddleOCR) to handle scanned books
2. Replace blind character-based chunking with semantic token-aware chunking
3. Make embedding models configurable instead of hardcoded
4. Support optional premium extraction via LlamaParse for problematic PDFs
5. Add IngestionPipeline for modular, cachable, extensible processing
6. Enable search reranking with multiple strategies (LLM, cross-encoder, reorder)
7. Expose Ragthen as a FastAPI + MCP server for remote access
8. Preserve the existing CLI interface and OpenCode agent experience

## Non-Goals

1. No changes to the ChromaDB storage backend (still ChromaDB, same path)
2. No changes to the Obsidian vault integration
3. No changes to the `ragthen ask` LLM call (still configurable, same format)
4. No changes to the OpenCode agent permissions or mode
5. No changes to the config file format or location
6. No semantic chunking for PDFs processed without LlamaParse (PDFPaddleOCR returns
   text per page, chunking applied by SentenceSplitter/SemanticChunker)

## Architecture Decisions

### D1: LlamaIndex as Core Engine

We wrap LlamaIndex in a `LlamaIndexEngine` class that implements the same
interface as the current `ragthen_core.engine` functions. The CLI and backends
import from this new engine without changing their code.

The wrapper handles:
- Ingestion: SimpleDirectoryReader + IngestionPipeline → VectorStoreIndex
- Search: VectorStoreIndex.as_retriever() + NodePostprocessors
- Ask: RetrieverQueryEngine with custom prompt templates
- Status/Clear/List: delegated to LlamaIndex + direct filesystem ops

_Rejected alternatives:_
- **Direct LlamaIndex API calls scattered across CLI** (tight coupling)
- **OOP inheritance from LlamaIndex** (over-engineered)

### D2: Tres modos de PDF Parser: auto, local, cloud

El parser de PDF tiene tres modos seleccionables via `--pdfparser` flag o
`pdfparser` en config.json:

| Modo | Flag | Comportamiento |
|------|------|----------------|
| Auto | `--pdfparser auto` (default) | Si hay `LLAMA_CLOUD_API_KEY`, usa LlamaParse (cloud) con fallback a PDFReader (pypdf) si cloud falla. Si no hay key, usa PDFReader (pypdf). |
| Local | `--pdfparser local` | Solo PDFReader (pypdf). Nunca cloud. Sin reintentos, sin sugerencias. |
| Cloud | `--pdfparser cloud` | Solo LlamaParse. Error si no hay `LLAMA_CLOUD_API_KEY` configurada. |
Precedencia: `--pdfparser` flag > `config.json > pdfparser` > default `auto`.

**Auto cloud**: si `LLAMA_CLOUD_API_KEY` esta configurada, usa LlamaParse primero
por su mejor calidad de extraccion (Markdown estructurado, OCR, layout). Si cloud
falla (red, rate limit), fallback silencioso a pypdf local.

**Auto local**: si no hay API key, usa PDFReader (pypdf) local. Sin cloud.

_Rejected alternatives:_
- **Single hardcoded reader** (no flexibility for edge cases)
- **Always ask user** (interrupts batch ingestion)

### D4: SentenceSplitter + SemanticChunker in IngestionPipeline

Two-stage chunking:
1. **SentenceSplitter** (always on): splits text by tokens, respecting sentence
   boundaries. Configurable `chunk_size` and `chunk_overlap`. Token-based, not
   character-based — no more truncation at 256 tokens.
2. **SemanticChunker** (optional): groups sentences by embedding similarity
   into semantically coherent chunks. Adaptive breakpoints based on similarity
   percentile.

Configuration: `chunking_strategy: sentence` (default) or `sentence+semantic`.
Existing `chunk_size` and `chunk_overlap` config values are used (but now in
tokens, not characters).

### D5: Configurable Embeddings via IngestionPipeline

The embedding model is set in `IngestionPipeline.transformations`. Default:
`text-embedding-3-large` (OpenAI, 3072d, 8192 tokens). Configurable via
config.json: `embedding_model` with variants:
- `openai:text-embedding-3-large`
- `openai:text-embedding-3-small`
- `huggingface:Alibaba-NLP/gte-Qwen2-7B-instruct`
- `huggingface:intfloat/multilingual-e5-large`
- `local:all-MiniLM-L6-v2` (backward compat)

### D6: Modular Reranking via NodePostprocessors

The QueryEngine uses `node_postprocessors` array. Configurable via config:
```json
{
  "reranker": {
    "type": "llm",
    "top_n": 10,
    "batch_size": 5
  }
}
```

Supported types: `llm` (LLMRerank), `cross-encoder` (SentenceTransformerRerank),
`cohere` (CohereRerank), `reorder` (LongContextReorder), `none`.

### D7: New raghten-server Package

Structure:
```
ragthen-server/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── src/
    └── raghten_server/
        ├── __init__.py
        ├── api.py              # FastAPI app, /ingest, /search, /ask, /status, /clear
        ├── mcp_server.py       # MCP tools: search, ask, status
        └── auth.py             # API key validation
```

The server reuses `LlamaIndexEngine` from raghten-core. It does NOT duplicate
the engine logic. The RemoteBackend client already exists in raghten-agent and
needs no changes — just configuration.

## Component Diagram

```
ragthen-agent/                    raghten-server/
  cli.py  ────┐                    api.py (FastAPI)
  backends/   │                    mcp_server.py (MCP SDK)
  ├─ local.py │                    auth.py
  └─ remote.py│                        │
               ▼                        ▼
        ┌──────────────────────────────────┐
        │     LlamaIndexEngine (wrapper)    │
        │  ┌────────────────────────────┐  │
        │  │  SimpleDirectoryReader     │  │
        │  │  PDFPaddleOCR / LlamaParse │  │
        │  │  SentenceSplitter          │  │
        │  │  SemanticChunker           │  │
        │  │  Metadata Extractors       │  │
        │  │  IngestionPipeline         │  │
        │  │  VectorStoreIndex          │  │
        │  │  ChromaVectorStore         │  │
        │  │  RetrieverQueryEngine      │  │
        │  │  NodePostprocessors        │  │
        │  └────────────────────────────┘  │
        └──────────────────────────────────┘
                        │
                        ▼
         ChromaDB (PersistentClient)
         ~/.ragthen/libraries/NAME/.chroma/
```

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| PDFReader (pypdf) fails on scanned PDFs | Medium | Auto fallback to LlamaParse en modo auto |
| SentenceSplitter chunks too large for embedding model | Low | Max chunk size enforced per model |
| SemanticChunker slow on large documents | Medium | IngestionPipeline cache; use only when enabled |
| LlamaParse cloud dependency changes/breaks | Low | Solo se usa en modo cloud o auto-fallback; pypdf es el default local |
| FastAPI + MCP server adds deployment complexity | Medium | Dockerfile + docker-compose included |
| Existing ChromaDB indices incompatible with new schema | Low | `ragthen clear -l NAME` and reingest needed |
