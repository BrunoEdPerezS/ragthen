# raghten-core — Delta Spec (LlamaIndex Migration)

## Purpose

Modified RAG engine that replaces the previous extraction, chunking, embedding,
and search pipeline with a LlamaIndex-based wrapper. Preserves the same
function signatures and output formats while improving PDF extraction quality
(OCR), chunking semantics (token/sentence-aware), and model flexibility.

## MODIFIED Requirements

### Document Ingestion

The ingestion pipeline is now modular via LlamaIndex `IngestionPipeline`.
Files are discovered via `SimpleDirectoryReader` (supports PDF, EPUB, TXT, MD,
DOCX, PPTX) and processed through configurable transformations.

**PDF Parser (tres modos):**

| Modo | Flag | Reader usado | Fallback | Sugerencia |
|------|------|-------------|----------|------------|
| Auto | `--pdfparser auto` (default) | PDFReader (pypdf) primero | Si 0 chunks, reintenta con LlamaParse | Si chunks < 20% de paginas, sugiere cloud |
| Local | `--pdfparser local` | PDFReader (pypdf) | No | No |
| Cloud | `--pdfparser cloud` | LlamaParse | No | No |

Precedencia: `--pdfparser` flag > `config.json > pdfparser` > default `auto`.
LlamaParse requiere `LLAMA_CLOUD_API_KEY` env var.

#### Scenario: Auto mode con PDF escaneado (fallback automatico)
Given a library containing a scanned PDF (no text layer)
When `ragthen ingest -l NAME` (default auto mode)
Then PDFReader (pypdf) extracts 0 chunks from the scanned PDF
And the engine detects 0 chunks and automatically retries with LlamaParse
And the LlamaParse result is used instead
And the user sees: "PDF X: fallback a LlamaParse (0 chunks de lector local)"

#### Scenario: Auto mode con sugerencia
Given a library with a PDF whose local extraction produces few chunks (e.g. 50 chunks for 300 pages)
When `ragthen ingest -l NAME` (default auto mode)
Then PDFReader (pypdf) extracts the PDF
But chunk count is below 20% of page count
And a suggestion is printed: "Sugerencia: pruebe --pdfparser cloud para mejor calidad en X"

#### Scenario: Local mode forzado
Given a library with a scanned PDF
When `ragthen ingest -l NAME --pdfparser local`
Then PDFReader (pypdf) is used
And if it produces 0 chunks, no fallback occurs
And the PDF is silently skipped

#### Scenario: Cloud mode forzado
Given a library with complex-layout PDFs
When `ragthen ingest -l NAME --pdfparser cloud`
Then each PDF is sent to LlamaParse cloud API
And the returned Markdown is used instead of local extraction
And EPUB/TXT/MD files use their standard readers

#### Scenario: Cloud mode sin API key
Given `LLAMA_CLOUD_API_KEY` is not set
When `ragthen ingest -l NAME --pdfparser cloud`
Then ingestion fails with: "Error: modo cloud requiere LLAMA_CLOUD_API_KEY"
And no PDFs are processed

### Chunking (IngestionPipeline Transformations)

SentenceSplitter runs by default, splitting text by tokens (not characters)
using `chunk_size` and `chunk_overlap` from config (now interpreted as tokens).

SemanticChunker is optional: when enabled, sentences are grouped by embedding
similarity. Breakpoints are determined by similarity percentile threshold.
Chunks never exceed `chunk_size` tokens; if a semantic group exceeds it,
SentenceSplitter sub-chunks that group.

#### Scenario: SentenceSplitter Only
Given text extracted from a document
When `chunking_strategy: "sentence"` (default)
Then SentenceSplitter divides text into chunks of `chunk_size` tokens
And no chunk crosses a sentence boundary
And `chunk_overlap` is applied in tokens between consecutive chunks

#### Scenario: Semantic + Sentence Chunking
Given a long document with multiple topics
When `chunking_strategy: "sentence+semantic"`
Then sentences are first grouped by embedding similarity
And groups below `chunk_size` are kept whole
And groups exceeding `chunk_size` are sub-chunked by SentenceSplitter
And each chunk has coherent topic (no topic mixing)

### Embedding Model

Previously hardcoded to `all-MiniLM-L6-v2`. Now configurable via config key
`embedding_model`. Format: `provider:model_name`.

| Provider | Example | Dims | Max Tokens |
|----------|---------|------|------------|
| openai | `text-embedding-3-large` | 3072 | 8192 |
| openai | `text-embedding-3-small` | 1536 | 8192 |
| huggingface | `intfloat/multilingual-e5-large` | 1024 | 514 |
| huggingface | `BAAI/bge-m3` | 1024 | 8192 |
| local | `all-MiniLM-L6-v2` (backward compat) | 384 | 256 |

#### Scenario: Custom Embedding Model
Given config with `embedding_model: "openai:text-embedding-3-large"`
When ingest() runs
Then OpenAI embedding API is used
And chunks up to 8192 tokens are accepted (not truncated)

#### Scenario: Backward Compatible Embedding
Given config with no `embedding_model` key (old config)
When ingest() runs
Then default `local:all-MiniLM-L6-v2` is used
And behavior is identical to the previous version

### Vector Storage

ChromaDB via `ChromaVectorStore` (LlamaIndex integration). Same underlying
ChromaDB PersistentClient, same path `~/.ragthen/libraries/NAME/.chroma/`.

Metadata per chunk: `source` (filename), `page` (page number), and any
additional metadata from extractors (title, keywords, etc.).

### Semantic Search and Reranking

`search()` uses `VectorStoreIndex.as_retriever(similarity_top_k)`, then applies
configured `NodePostprocessors`:

- **LLMRerank**: rerank via LLM, configurable `top_n` and `batch_size`
- **SentenceTransformerRerank**: cross-encoder (equivalent to previous pipeline)
- **LongContextReorder**: reorder nodes for optimal LLM context placement
- **None**: no reranking, return raw similarity scores

Output format: same JSON structure as before:
```json
[
  {"source": "file.pdf", "page": 42, "relevance": 0.95, "text": "..."}
]
```

`relevance` field preserved for backward compatibility (maps from LlamaIndex
score).

#### Scenario: Search with LLM Reranker
Given an indexed library
When `ragthen search -l NAME "query" --rerank --top 10`
Then the retriever returns top 30 candidates
And LLMRerank selects top 10
And each result includes source, page, relevance, and text

#### Scenario: Search Without Reranker
Given an indexed library
When `ragthen search -l NAME "query" --top 10` (no --rerank)
Then the retriever returns top 10 directly
And scores are raw cosine similarities
And no reranking is applied

### LLM-Powered Ask

`ask()` uses `RetrieverQueryEngine` with `CitationQueryEngine` for automatic
citation generation. Same invocation: `ragthen ask -l NAME "question" --api-key KEY`.

Returns response with cited sources in format `[Source: file, Page X, Score: Y]`.
If no API key provided, returns raw search context (same as before).

## REMOVED Requirements

The following modules from the previous implementation are removed:

- `storage.py`: PDF extraction via PyMuPDF (`page.get_text()`) — replaced by
  `SimpleDirectoryReader` + `PDFReader` (pypdf) / LlamaParse
- `rerank.py`: Cross-encoder reranker — replaced by
  SentenceTransformerRerank (node postprocessor)
- `engine.py` functions: replaced by LlamaIndexEngine class wrapper
- Hardcoded embedding model `all-MiniLM-L6-v2` — replaced by configurable
- Character-based sliding window chunking — replaced by SentenceSplitter

## ADDED Requirements

### LlamaIndex Dependencies

`llama-index-core`, `llama-index-vector-stores-chroma`, and reader-specific
packages are core dependencies. They are imported lazily only when ingestion
or search is invoked. Missing optional dependencies (e.g. LlamaParse) print
a message and skip the feature without crashing.

### Section-Based Citation Metadata

Each chunk is enriched with the nearest preceding heading as `section` metadata.
This enables citation by document section when page numbers are unavailable
(e.g. LlamaParse cloud output).

After the IngestionPipeline produces nodes, `_enrich_section_metadata()` scans
each node's text for Markdown headings (`#`, `##`, etc.) and tracks the most
recent heading seen. That heading is saved as `node.metadata["section"]`.

The `search` output includes `section` when available, alongside `source`, `page`,
`relevance`, and `text`.

#### Scenario: Cloud ingestion with section metadata
Given a PDF parsed via LlamaParse (Markdown output with headings)
When the ingestion pipeline processes the nodes
Then each chunk from section "Chapter 2" has `metadata.section = "Chapter 2"`
And the search JSON output includes `"section": "Chapter 2"`
And the agent can cite: `[Fuente: filename, Encabezado: "Chapter 2"]`

### Library Re-ingestion

Libraries indexed with the previous pipeline must be cleared and re-ingested.
The ChromaDB schema and metadata format may differ. `ragthen clear -l NAME`
followed by `ragthen ingest -l NAME` is required for existing libraries.
