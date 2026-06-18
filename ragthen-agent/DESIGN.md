# Ragthen Agent — Design & Architecture

## Role

Ragthen is a **read-only research agent**. It searches indexed libraries and
returns context with citations. It does NOT edit files, write notes, or modify
the user's workspace. The agent that invokes Ragthen (Build, Plan, etc.) owns
the decision of what to do with the results.

## Agent Mode

```
mode: all
```

- `all` means Ragthen is both **TAB-switchable** (primary agent) and
  **invocable as a subagent** via `@ragthen` or the Task tool.
- This allows Plan/Build to delegate research to Ragthen, receive cited context,
  and integrate it into their own output.

## Permissions

```yaml
permission:
  bash:
    "ragthen *": allow
  read: allow
  edit: deny
  webfetch: deny
  websearch: deny
```

| Permission | Value | Rationale |
|---|---|---|
| `bash: "ragthen *"` | allow | All library operations (search, ingest, clear, status) go through CLI |
| `read` | allow | Needed to inspect library files and results |
| `edit` | deny | Ragthen is NOT an editor. Mutations are done via CLI commands only |
| `webfetch` | deny | External knowledge is prohibited — library-only |
| `websearch` | deny | External knowledge is prohibited — library-only |

## Separation of Concerns (SOC)

```
Primary Agent (Plan/Build)     Ragthen (subagent)
─────────────────────────     ──────────────────
Decides what to research  →   Executes ragthen search
Receives cited context    ←   Returns JSON with [Source, Page X]
Decides to write or not        NEVER writes files
```

Ragthen's contract:
1. Search the library
2. Synthesize findings with citations
3. Return context to the caller

The caller decides whether to create an Obsidian note, update a file, or just
display the results. Ragthen never makes that decision.

## Library Management (via CLI, not edit tool)

All mutations to libraries happen through `ragthen` commands, which run as
subprocesses (`bash` permission). The `edit` tool is never used.

| Operation | Command | What it does |
|---|---|---|
| Index files | `ragthen ingest -l NAME` | Chunks PDFs/TXTs/MDs, embeds with all-MiniLM-L6-v2, stores in ChromaDB |
| Search | `ragthen search -l NAME "query" --rerank --top N` | Semantic search + cross-encoder rerank, returns JSON |
| Status | `ragthen status -l NAME` | Shows chunk count and indexed documents |
| Clear index | `ragthen clear -l NAME` | Deletes ChromaDB index via `shutil.rmtree` |
| List libraries | `ragthen libraries` | Lists all libraries under `~/.ragthen/libraries/` |
| Config | `ragthen config` | Shows current configuration |
| Vault ingest | `ragthen vault ingest -l NAME --vault PATH` | Copies Obsidian notes into a library and indexes them |

## Commands the Agent Uses

The agent prompt (`Ragthen.md`) instructs Ragthen to use only:

- `ragthen libraries` — discover available libraries
- `ragthen search -l NAME "query" --rerank --top N` — semantic search
- `ragthen status -l NAME` — inspect library contents
- `ragthen config` — check configuration

`ragthen ask` is explicitly forbidden in the agent prompt — Ragthen IS the LLM
and must synthesize answers itself from the raw search results.

## Architecture

```
ragthen-agent/          ← Agent definition + CLI + backends
├── .opencode/
│   ├── agents/
│   │   └── Ragthen.md          ← Opencode agent (portable with the repo)
│   └── skills/
│       └── analisis-multifuente/
│           └── SKILL.md        ← Cross-source deep analysis skill
├── src/ragthen_agent/
│   ├── cli.py                  ← argparse CLI entry point (ragthen command)
│   ├── vault.py                ← Obsidian vault note scanning
│   └── backends/
│       ├── interface.py        ← Backend ABC
│       ├── local.py            ← ChromaDB + sentence-transformers
│       └── remote.py           ← API server backend (future)
├── bootstrap.ps1               ← Windows install script
├── pyproject.toml
└── DESIGN.md                   ← This file

ragthen-core/           ← RAG engine (library dependency)
├── src/ragthen_core/
│   ├── config.py               ← Config loading (~/.ragthen/config.json)
│   ├── engine.py               ← ingest, search, ask, status, clear
│   ├── storage.py              ← ChromaDB collection + PDF/TXT extraction
│   └── rerank.py               ← Cross-encoder reranking
├── pyproject.toml
└── requirements.txt

ragthen-content/        ← Library structure docs and sync scripts
```

## Data Flow

```
PDF/TXT/MD files  →  ragthen ingest  →  ChromaDB chunks
                                              │
User question     →  ragthen search  →  JSON [{source, page, relevance, text}]
                                              │
Ragthen agent     →  synthesizes     →  Cited answer [Source: file, Page X]
```

## Portability

Everything needed to deploy Ragthen as an opencode agent travels with the repo
inside `ragthen-agent/.opencode/`. Clone the repo, run `bootstrap.ps1`, and
opencode picks up the agent and skill automatically from the project-level
`.opencode/` directory.
