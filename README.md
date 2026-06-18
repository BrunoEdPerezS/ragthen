# Ragthen

RAG agent with local/remote backends. Indexes PDFs and Obsidian vault notes into
searchable ChromaDB libraries.

## Structure

```
ragthen-core/     # RAG engine: ingest, search, ChromaDB, embeddings, rerank
ragthen-agent/    # CLI + Strategy-pattern backends (local/remote)
ragthen-content/  # Library structure docs, sync scripts
```

## Quick start

```powershell
# 1. Bootstrap (installs both packages, creates config)
.\ragthen-agent\bootstrap.ps1

# 2. Add PDFs to ~/.ragthen/libraries/<name>/

# 3. Index and search
ragthen ingest -l mylib
ragthen search -l mylib "your query"
```

## Config

Edit `~/.ragthen/config.json`:

```json
{
  "backend_mode": "local",
  "vault_path": "C:/path/to/obsidian/vault",
  "libraries_path": "~/.ragthen/libraries"
}
```

Set `backend_mode` to `"remote"` when the API server is ready.
