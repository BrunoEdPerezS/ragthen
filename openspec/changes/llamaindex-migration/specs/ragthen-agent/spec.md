# raghten-agent — Delta Spec (LlamaIndex Migration)

## Purpose

Adapted CLI and backends that use the new LlamaIndex-based engine. The CLI
interface, output format, and agent definition remain backward compatible.

## MODIFIED Requirements

### CLI Entry Point

Same subcommands: `ingest`, `search`, `ask`, `status`, `clear`, `libraries`,
`config`, `vault ingest`.

**New flags added:**

| Flag | Affected Command | Description |
|------|-----------------|-------------|
| `--pdfparser` | `ingest` | PDF parser mode: `auto` (default, fallback automatico), `local` (solo OCR local), `cloud` (solo LlamaParse) |
| `--chunking` | `ingest` | Chunking strategy: `sentence` (default), `sentence+semantic` |
| `--reranker` | `search` | Reranker type: `llm`, `cross-encoder`, `reorder`, `none` |

Existing flags (`-l`, `--rerank`, `--top`, `--api-key`) remain functional.

### Local Backend

`LocalBackend` now imports `LlamaIndexEngine` from `ragthen_core.llama_engine`
instead of the old `ragthen_core.engine` functions. Interface unchanged:

- `ingest(library_name, files, pdfparser_mode, chunking_strategy)`
- `search(library_name, query, top_n, rerank, reranker_type)`
- `ask(library_name, query, api_key)`
- `status(library_name)`
- `clear(library_name)`
- `list_libraries()`

### Remote Backend

No changes. The `RemoteBackend` already sends HTTP POST requests with the
correct JSON payloads. It will connect to the new `ragthen-server`.

### OpenCode Agent (Ragthen.md)

**Citation format updated:**
- Old: `[Source: filename, Page X]` con numeros de pagina
- New: `[Fuente: filename, Encabezado: "Section Title"]` con secciones
- El `page` field se conserva en el JSON pero el agente prioriza la seccion cuando esta disponible

No structural changes to the agent prompt. The agent uses the same commands:
`ragthen search`, `ragthen libraries`, `ragthen status`, `ragthen config`.

**Verification needed:**
- JSON output fields are identical (`source`, `page`, `relevance`, `text`)
- Error messages follow the same format
- Fallback interactive options unchanged

If the `relevance` score range differs (e.g. LlamaIndex uses 0-1 same as
before), no agent adjustments needed.

## ADDED Requirements

### Reader/Chunker Flags Awareness

The agent prompt in `Ragthen.md` should mention the new flags for
power users who want to override defaults:
- `ragthen ingest -l NAME --pdfparser cloud` for problematic PDFs
- `ragthen search -l NAME "query" --reranker llm` for LLM-reranked search
