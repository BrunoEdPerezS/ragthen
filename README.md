# Raghtena

RAG agent with local/remote backends. Indexes PDFs and Obsidian vault notes into
searchable ChromaDB libraries.

## Structure

```
ragthtena-core/     # RAG engine: ingest, search, ChromaDB, embeddings, rerank
ragthtena-agent/    # CLI + Strategy-pattern backends (local/remote)
ragthtena-content/  # Library structure docs, sync scripts
```

## Quick start

```powershell
# 1. Bootstrap (installs both packages, creates config)
.\ragthtena-agent\bootstrap.ps1

# 2. Add PDFs to ~/.ragthtena/libraries/<name>/

# 3. Index and search
ragthtena ingest -l mylib
ragthtena search -l mylib "your query"
```

## Config

Edit `~/.ragthtena/config.json`:

```json
{
  "backend_mode": "local",
  "vault_path": "C:/path/to/obsidian/vault",
  "libraries_path": "~/.ragthtena/libraries"
}
```

Set `backend_mode` to `"remote"` when the API server is ready.
