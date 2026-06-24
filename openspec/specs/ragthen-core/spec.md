# ragthen-core

## Purpose
RAG engine library providing configuration, document ingestion, semantic search, cross-encoder reranking, and LLM-powered Q&A. Depended on by `ragthen-agent`.

## Requirements

### Requirement: Config Loading
The system SHALL load configuration from `~/.ragthen/config.json` with auto-creation of defaults on first run. Config SHALL be cached globally after first load.

Default values:
- `backend_mode`: "local"
- `libraries_path`: "~/.ragthen/libraries"
- `chunk_size`: 1200
- `chunk_overlap`: 250
- `llm_model`: "gpt-4o"

#### Scenario: First run with no config file
- **WHEN** `load_config()` is called and `~/.ragthen/config.json` does not exist
- **THEN** the system creates the config file with default values, creates the libraries directory, and returns the default config dict

#### Scenario: Config file exists and is valid
- **WHEN** `load_config()` is called and a valid `config.json` exists
- **THEN** the system parses and returns the config, caching it for subsequent calls

#### Scenario: Config file exists but is corrupt
- **WHEN** `load_config()` is called and `config.json` contains invalid JSON
- **THEN** the system falls back to creating a new default config

### Requirement: Library Resolution
The system SHALL resolve library names to their directory paths under `~/.ragthen/libraries/<name>/`. If no name is provided and exactly one library exists, it SHALL auto-detect. If multiple libraries exist and no name is provided, it SHALL list them and exit with error.

#### Scenario: Single library, no name provided
- **WHEN** `resolve_library()` is called with `name=None` and exactly one library exists
- **THEN** the system returns the path to that library's directory and its `.index/` subdirectory

#### Scenario: Zero libraries
- **WHEN** `resolve_library()` is called and no libraries exist
- **THEN** the system prints instructions for creating a library and exits with code 1

#### Scenario: Multiple libraries, no name provided
- **WHEN** `resolve_library()` is called with `name=None` and multiple libraries exist
- **THEN** the system lists all available libraries and exits with code 1

### Requirement: Document Ingestion
The system SHALL ingest PDF, TXT, and MD files from a library directory into a ChromaDB collection. PDFs SHALL be parsed with PyMuPDF (fitz) extracting page-level text. TXT and MD files SHALL be read directly. Text SHALL be chunked with configurable size and overlap. Chunks SHALL be embedded using `all-MiniLM-L6-v2` via sentence-transformers and stored in ChromaDB with metadata (source filename, page number).

#### Scenario: Library contains PDFs, TXTs, and MDs
- **WHEN** `ingest()` is called on a library directory containing a mix of file types
- **THEN** all files are processed, their text extracted, chunked, embedded, and stored in the ChromaDB index with source and page metadata

#### Scenario: Library has no processable files
- **WHEN** `ingest()` is called on a directory with no PDF, TXT, or MD files
- **THEN** the system prints a message indicating no files were found and returns without error

#### Scenario: PDF file has no extractable text
- **WHEN** a PDF yields empty text for all pages
- **THEN** the system skips that file with a message "(no extractable text, skipping)"

### Requirement: Semantic Search
The system SHALL embed a query using the same embedding model, query ChromaDB for the nearest neighbors using cosine distance, and return results with source, page, relevance score, and text. Relevance score SHALL be computed as `max(0, 1 - distance/2)`.

#### Scenario: Basic search
- **WHEN** `search()` is called with a query and `rerank=False`
- **THEN** results are returned ordered by vector similarity with relevance scores in [0, 1]

#### Scenario: Search with relevance threshold
- **WHEN** `search()` is called with `relevance_threshold > 0`
- **THEN** results with relevance below the threshold are filtered out

#### Scenario: Search with reranking enabled
- **WHEN** `search()` is called with `rerank=True`
- **THEN** the system retrieves `top_k * 3` candidates from ChromaDB, then passes them through the cross-encoder reranker, returning only the top `top_k` reranked results

### Requirement: Cross-Encoder Reranking
The system SHALL provide a rerank function that uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to rescore passages against the query. Reranking SHALL convert raw scores to [0, 1] via sigmoid and sort descending by relevance.

#### Scenario: Reranking available
- **WHEN** `rerank()` is called with a query and list of passages
- **THEN** passages are rescored, sorted by relevance descending, and the top N are returned

#### Scenario: Reranker not available
- **WHEN** the cross-encoder model fails to load
- **THEN** the system prints a warning to stderr and falls back to returning the first `top_k` passages from the original results

### Requirement: LLM-Powered Ask
The system SHALL support `ask()` which searches the library, formats results as context with a prompt template, and optionally calls OpenAI to generate a cited answer. If no API key is provided, the raw context is returned instead.

#### Scenario: Ask with API key
- **WHEN** `ask()` is called with a valid `api_key`
- **THEN** the system searches the library, formats context, calls OpenAI with the prompt template, and returns the LLM response

#### Scenario: Ask without API key
- **WHEN** `ask()` is called with `api_key=None`
- **THEN** the system returns the raw context passages formatted with source citations, without making an API call

### Requirement: Library Status
The system SHALL display the number of indexed chunks and list of unique document sources in a library's ChromaDB collection.

#### Scenario: Indexed library
- **WHEN** `status()` is called on a library with an existing ChromaDB index
- **THEN** the chunk count and list of unique source filenames are printed

#### Scenario: Unindexed library
- **WHEN** `status()` is called on a library with no index
- **THEN** a message is printed indicating no index exists and suggesting to run ingest

### Requirement: Clear Index
The system SHALL delete a library's ChromaDB index directory via `shutil.rmtree`.

#### Scenario: Index exists
- **WHEN** `clear()` is called on a library with an existing `.index/` directory
- **THEN** the directory is removed and a confirmation message is printed

#### Scenario: No index
- **WHEN** `clear()` is called on a library with no index
- **THEN** a message is printed indicating nothing to clear

### Requirement: List Libraries
The system SHALL list all subdirectories under `~/.ragthen/libraries/` that don't start with `.` or `_`, showing their index status (chunk count or "not indexed").

#### Scenario: Libraries exist
- **WHEN** `list_libraries()` is called
- **THEN** all valid library directories are listed with their chunk count if indexed, or "(not indexed)" otherwise

#### Scenario: No libraries
- **WHEN** `list_libraries()` is called and no library directories exist
- **THEN** a message with instructions to create a library is printed
