# raghten-server — Specification

## Purpose

FastAPI + MCP server that exposes Ragthen's RAG capabilities as remote
endpoints. Enables remote access from internet-connected clients, including
OpenCode agents via MCP protocol and custom applications via REST API.

## Requirements

### R1: FastAPI REST API

The server provides the following endpoints, all gated by API key authentication
via `X-API-Key` header:

#### POST /ingest
- **Body**: `{"library": "name", "reader": "pdfpaddleocr"|"llamaparse", "chunking": "sentence"|"sentence+semantic"}`
- **Action**: Scans the library directory and ingests any new/changed files
- **Response**: `{"status": "ok", "chunks": 1234, "files": 5}`
- **Error**: `{"status": "error", "message": "..."}`
- **Scenario**: Library exists → ingest and return chunk count
- **Scenario**: Library does not exist → 404 error
- **Scenario**: No API key → 401 error

#### POST /search
- **Body**: `{"library": "name", "query": "...", "top_n": 10, "reranker": "llm"|"cross-encoder"|"none"}`
- **Response**: `{"results": [{"source": "file.pdf", "page": 42, "relevance": 0.95, "text": "..."}]}`
- **Scenario**: Library found, results exist → return array
- **Scenario**: Library found, no results → return empty array
- **Scenario**: Library not found → 404

#### POST /ask
- **Body**: `{"library": "name", "query": "...", "api_key": "sk-..."}`
- **Response**: `{"answer": "...", "sources": [{"source": "file.pdf", "page": 42, "relevance": 0.95}]}`
- **Scenario**: Valid API key → LLM answer with citations
- **Scenario**: No API key → 400 error (ask requires LLM)
- **Scenario**: Library found but empty → informative message

#### POST /status
- **Body**: `{"library": "name"}`
- **Response**: `{"library": "name", "chunks": 1234, "documents": ["file1.pdf", "file2.pdf"]}`
- **Scenario**: Library exists → return stats
- **Scenario**: Library does not exist → 404

#### POST /clear
- **Body**: `{"library": "name"}`
- **Response**: `{"status": "ok", "message": "Library 'name' index cleared"}`
- **Scenario**: Library exists → delete index
- **Scenario**: Library does not exist → 404

### R2: MCP Server

Server implements the Model Context Protocol (MCP) using Anthropic's MCP SDK.
Exposes tools:

- `search(library: str, query: str, top_n: int = 10) -> list`
- `ask(library: str, question: str) -> str`
- `status(library: str) -> dict`

These tools are callable by any MCP-compatible client (OpenCode, Claude Desktop,
VS Code extensions, etc.).

#### Scenario: MCP Search Tool
Given a configured MCP client
When the client calls `search("marketing", "What is pricing?", 5)`
Then the server returns a list of 5 results with source, page, score, and text

### R3: API Key Authentication

- API key validated as bearer token in `X-API-Key` header
- Key stored in environment variable `RAGTHEN_API_KEY`
- If env var is not set, the server prints a warning on startup and allows
  unauthenticated access (development mode)
- All endpoints return 401 with `{"detail": "Invalid API key"}` on auth failure

### R4: Docker Deployment

- `Dockerfile`: Python 3.11, installs raghten-core and raghten-server
- `docker-compose.yml`: maps port 8000, mounts `~/.ragthen/` volume,
  passes `OPENAI_API_KEY`, `RAGTHEN_API_KEY`, `LLAMA_CLOUD_API_KEY` env vars
- Server listens on `0.0.0.0:8000` inside container
- Health check at `GET /health` returning `{"status": "ok"}`

### R5: Configuration

The server reads `~/.ragthen/config.json` for shared settings (chunk_size,
embedding_model, etc.). Overrides via environment variables with `RAGTHEN_`
prefix.

#### Scenario: Local Config Fallback
Given no environment variable overrides
When the server starts
Then it reads `~/.ragthen/config.json`
And applies those settings for ingestion and search

#### Scenario: Env Var Override
Given `RAGTHEN_CHUNK_SIZE=2000` set
When the server starts
Then it uses chunk_size = 2000 instead of the config file value
