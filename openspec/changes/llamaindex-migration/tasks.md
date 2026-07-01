# LlamaIndex Migration — Tasks

## Phase 1: Evaluar --pdfparser auto/local/cloud [COMPLETED]

La migracion a LlamaIndex ya esta decidida. Esta fase solo define el
comportamiento del parser de PDF (que reader usar y cuando).

Resultados de la evaluacion:
- Encoding: los acentos NO estan corruptos. Los bytes extraidos por PyMuPDF
  y pypdf contienen los caracteres correctos (ó, é, í, ©). El � era un
  problema de display del terminal de Windows.
- Paginas vacias: pypdf recupera texto donde PyMuPDF devuelve 0 chars.
- PaddleOCR: no funciona confiablemente en Windows/Python 3.13.
  Se descarta como reader local.
- Reader local elegido: `PDFReader` (pypdf) — mas liviano y compatible.
- Scanned PDFs: no hay en las librerias actuales para probar.
  El fallback a LlamaParse queda implementado pero sin casos de prueba reales.

- [x] Evaluar PDFPaddleOCR — descartado (incompatible con Python 3.13 en Windows)
- [x] Evaluar PDFReader (pypdf) — seleccionado como reader local default
- [x] Evaluar PyMuPDFReader — equivalente al actual, reemplazado por pypdf
- [x] Evaluar pdfplumber — compatible, pero pypdf es igual de bueno
- [x] Evaluar PaddleOCR — incompatible, no usado
- [x] Confirmar que encoding no es problema real

## Phase 2: Migrate ragthen-core [COMPLETED]

- [x] Add LlamaIndex dependencies to `ragthen-core/pyproject.toml`:
  - `llama-index-core`
  - `llama-index-vector-stores-chroma`
  - `llama-index-readers-file` (provee PDFReader con pypdf)
  - `llama-parse` (optional, lazy import)
  - `llama-index-llms-openai`, `llama-index-embeddings-openai`, `llama-index-embeddings-huggingface`
- [x] Create `ragthen-core/src/ragthen_core/llama_engine.py`:
  - `LlamaIndexEngine` class wrapping ingestion, search, ask, status, clear
  - `SimpleDirectoryReader` with configurable file readers
  - `PDFReader` (pypdf) reader integration (default local)
  - `LlamaParse` reader integration (optional, flagged)
  - `SentenceSplitter` with configurable chunk_size/chunk_overlap
  - `SemanticChunker` (optional, configurable)
  - `IngestionPipeline` combining readers + chunkers + embeddings
  - `ChromaVectorStore` + `VectorStoreIndex`
  - `RetrieverQueryEngine` with `NodePostprocessors` for reranking
- [x] Replace `ragthen-core/src/ragthen_core/engine.py`:
  - Imports and re-exports from `llama_engine.py`
  - Same function signatures: `ingest()`, `search()`, `ask()`, `status()`, `clear()`, `list_libraries()`
- [x] Remove `ragthen-core/src/ragthen_core/storage.py` (handled by LlamaIndex readers)
- [x] Remove `ragthen-core/src/ragthen_core/rerank.py` (handled by LlamaIndex postprocessors)
- [x] Update `ragthen-core/src/ragthen_core/config.py`:
  - Add new config keys: `pdfparser`, `embedding_model`, `chunking_strategy`, `reranker`
  - Backward compatibility with existing config (defaults for new keys)
- [x] Update `ragthen-core/src/ragthen_core/__init__.py`:
  - Re-export new functions
- [x] Update `ragthen-core/pyproject.toml`:
  - Remove: `pymupdf` (deprecated), `ebooklib` (deprecated), `markdownify` (deprecated)
  - Keep: `chromadb`, `openai`, `sentence-transformers` (still used by some rerankers)
  - Add: LlamaIndex packages

## Phase 3: Adapt raghten-agent [COMPLETED]

- [x] Adapt `ragthen-agent/src/ragthen_agent/cli.py`:
  - `ingest` command: add `--pdfparser` flag (auto / local / cloud)
  - `ingest` command: add `--chunking` flag (sentence / sentence+semantic)
  - All commands: output format unchanged
- [x] Adapt `ragthen-agent/src/ragthen_agent/backends/local.py`:
  - Import `llama_engine` instead of old `engine`
  - Same interface, no signature changes
  - New params: pdfparser_mode, chunking_strategy, reranker_type
- [x] Adapt `ragthen-agent/src/ragthen_agent/backends/remote.py`:
  - Updated signatures to match interface
- [x] Verify `ragthen-agent/.opencode/agents/Ragthen.md`:
  - JSON output format identical (source, page, relevance, text)
  - New flags added to Available commands section
- [x] Update `ragthen-agent/pyproject.toml`:
  - Keep dependency on `ragthen-core`

## Phase 4: Build raghten-server [FUTURE WORK]

- [ ] Create `ragthen-server/pyproject.toml`
- [ ] Implement REST API endpoints
- [ ] Implement MCP server
- [ ] Create Dockerfile + docker-compose.yml

## Phase 5: Testing and Deployment

- [ ] Citation enrichment:
  - [x] Implement `_enrich_section_metadata()` en llama_engine.py
  - [x] Aplicar la funcion despues de pipeline.run() en ingesta
  - [x] Actualizar formato de citas en Ragthen.md
  - [ ] Re-ingestar librerias para generar metadata de secciones
- [ ] Full integration test:
  - [x] Ingest library with PDFReader (pypdf) — Thinksight verificado (1184 chunks)
  - [x] Search with SentenceTransformerRerank — verificado
  - [x] `ragthen status` y `ragthen libraries` — verificado
  - [ ] Ingest library with LlamaParse (requires API key)
  - [ ] Search with LLMRerank
  - [ ] `ragthen ask` with citations
  - [ ] Backward compatibility: old library re-ingestion
- [ ] Remote test:
  - [ ] Start raghten-server locally
  - [ ] Connect via RemoteBackend (`backend_mode: remote`)
  - [ ] Connect via MCP client (e.g. OpenCode MCP)
  - [ ] Test search, ask, status remotely
- [ ] Authentication test:
  - [ ] Valid API key → access granted
  - [ ] Invalid/missing API key → 401 rejected
- [ ] Reingest all existing libraries:
  - [ ] Retsell library (marketing books)
  - [ ] Thinksight library (done)
  - [ ] Finsight, Socsight
- [ ] Deploy on miniserver:
  - [ ] `docker-compose up -d` on server
  - [ ] Configure `KHOJ_DOMAIN` + SSL for remote access
  - [ ] Update `~/.ragthen/config.json` on client: `backend_mode: remote`,
    `remote_url: https://server:8000`
