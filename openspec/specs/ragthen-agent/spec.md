# ragthen-agent

## Purpose
CLI, backends (local/remote), Obsidian vault integration, and opencode agent definition for the Ragthen RAG system. Depends on `ragthen-core`.

## Requirements

### Requirement: CLI Entry Point
The system SHALL expose a `ragthen` CLI command via argparse with the following subcommands: `ingest`, `search`, `ask`, `status`, `clear`, `libraries`, `config`, and `vault ingest`. The CLI SHALL be defined in `ragthen_agent.cli:main` and registered as a console script in pyproject.toml.

#### Scenario: No arguments
- **WHEN** `ragthen` is invoked with no arguments
- **THEN** the help text is printed

#### Scenario: Search with reranking
- **WHEN** `ragthen search -l mylib "query" --rerank --top 10` is invoked
- **THEN** the backend performs a semantic search with cross-encoder reranking and prints JSON results

#### Scenario: Search output encoding
- **WHEN** search results contain characters that can't be encoded in the terminal's encoding
- **THEN** `_safe_print` falls back to ASCII with replacement characters

### Requirement: Backend Abstraction
The system SHALL define an abstract `Backend` ABC with methods: `ingest()`, `search()`, `ask()`, `status()`, `clear()`, and `list_libraries()`. Concrete implementations SHALL be `LocalBackend` and `RemoteBackend`.

#### Scenario: Local backend instantiation
- **WHEN** `backend_mode` is "local" in config
- **THEN** `_get_backend()` returns a `LocalBackend` instance

#### Scenario: Remote backend instantiation
- **WHEN** `backend_mode` is "remote" in config
- **THEN** `_get_backend()` returns a `RemoteBackend` instance

### Requirement: Local Backend
The `LocalBackend` SHALL use `ragthen-core` functions directly as a Python library with zero network calls. Each method SHALL delegate to the corresponding `ragthen_core.engine` function after resolving the library path.

#### Scenario: Local ingest
- **WHEN** `LocalBackend.ingest("mylib")` is called
- **THEN** the library directory is resolved, PDFs/TXTs/MDs are chunked, embedded, and stored in ChromaDB

#### Scenario: Local search
- **WHEN** `LocalBackend.search("query", "mylib")` is called
- **THEN** the ChromaDB index is queried and a list of result dicts with source, page, relevance, and text is returned

### Requirement: Remote Backend
The `RemoteBackend` SHALL communicate with a Ragthen API server via HTTP POST requests to endpoints `/ingest`, `/search`, `/ask`, `/status`, `/clear`, and `/libraries`. Errors SHALL be printed to stderr and return empty results.

#### Scenario: Successful remote search
- **WHEN** `RemoteBackend.search("query", "mylib")` is called and the server responds with 200
- **THEN** results are extracted from the JSON response under the `"results"` key

#### Scenario: HTTP error from remote server
- **WHEN** the server returns an HTTP error code
- **THEN** the error code and body are printed to stderr, and an empty result is returned

#### Scenario: Connection error
- **WHEN** the server is unreachable
- **THEN** the error is printed to stderr and an empty result/empty answer is returned

### Requirement: Obsidian Vault Integration
The system SHALL provide vault operations: `resolve()` to find the vault path from config or CLI args, `scan_notes()` to discover all `.md` files in a vault while skipping hidden directories, and `read_note()` to read note content.

#### Scenario: Vault ingest
- **WHEN** `ragthen vault ingest -l mylib --vault /path/to/vault` is invoked
- **THEN** all `.md` notes are scanned, copied to the library directory with `_vault_` prefix, and indexed into ChromaDB

#### Scenario: No vault path configured
- **WHEN** `ragthen vault ingest -l mylib` is invoked without `--vault` and no `vault_path` in config
- **THEN** a message is printed indicating no vault path is set

#### Scenario: Vault directory doesn't exist
- **WHEN** `scan_notes()` is called with a non-existent path
- **THEN** an empty dict is returned

### Requirement: Opencode Agent Definition
The system SHALL include an opencode agent definition at `ragthen-agent/.opencode/agents/Ragthen.md` with `mode: all`, locked-down permissions (bash: ragthen*, read: allow, edit/webfetch/websearch: deny), and a prompt that enforces library-only knowledge with mandatory source citations.

#### Scenario: Agent invoked as primary
- **WHEN** the user switches to Ragthen via Tab in opencode
- **THEN** the agent searches the library, synthesizes an answer with `[Source: filename, Page X]` citations, and never uses external knowledge

#### Scenario: Agent invoked as subagent
- **WHEN** Plan or Build delegates a task to Ragthen via `@ragthen`
- **THEN** Ragthen searches the library and returns cited context without modifying any files

#### Scenario: Low relevance results
- **WHEN** search returns <3 results or all results have relevance <0.25
- **THEN** the agent alerts the user and offers interactive fallback options (broader terms, status check, different library, continue anyway)

### Requirement: Analisis Multifuente Skill
The system SHALL include a skill at `ragthen-agent/.opencode/skills/analisis-multifuente/SKILL.md` that executes N+1 targeted searches per source, builds an integrated cross-source model with ASCII diagrams, and generates a 7-section Obsidian note with page-level citations.

#### Scenario: Deep cross-source analysis
- **WHEN** the analisis-multifuente skill is invoked with a library name and topic
- **THEN** it executes a generic search plus one directed search per source using each source's vocabulary, extracts findings, builds an integrated model, and writes an Obsidian note with all 7 required sections
