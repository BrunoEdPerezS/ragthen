---
name: analisis-multifuente
description: Cross-source deep analysis from Ragthen libraries. Executes targeted searches per source, integrates multiple perspectives into a single coherent model with page-level citations, and generates actionable Obsidian notes with proper Spanish orthography.
license: MIT
compatibility: opencode
metadata:
  audience: research
  requires: ragthen-agent
---

# Analisis Multifuente con Ragthen

## What I do

Generate deep, actionable analyses by cross-referencing **multiple sources** from a Ragthen library. Each source covers a different angle of the same topic. I execute targeted searches for each source using its own vocabulary, extract the unique contribution of each, and weave them into a coherent integrated model with every claim backed by a page-level citation. I also create well-formatted Obsidian vault notes with the results.

## When to use me

Use this skill when the user asks to:
- Analyze a topic across multiple books/documents in a library
- Get a recommendation backed by multiple sources
- Create an Obsidian note that integrates findings from multiple perspectives
- Run a "deep analysis" instead of a simple search

## How I work

### Step 1 — Identify what each source contributes

Before searching, answer for each document in the library:

| Question | Example |
|----------|---------|
| What is this book's main topic? | Kotler: pricing theory. Mkt 4.0: digital era. Roberge: scalable sales |
| What unique angle does it bring? | Kotler: the WHAT. Mkt 4.0: HOW the customer perceives it. Roberge: HOW to execute |
| What keywords are unique to this book? | Use terms from its own index/glossary, not generic synonyms |

### Step 2 — Execute targeted searches (N+1 strategy)

Run **one generic search** plus **one directed search per source**, each using `--rerank`:

```bash
# Generic (panorama)
ragthen search -l LIB "generic topic terms" --rerank --top 8

# Per source (use each source's own vocabulary)
ragthen search -l LIB "source-A-unique-terms" --rerank --top 5
ragthen search -l LIB "source-B-unique-terms" --rerank --top 5
ragthen search -l LIB "source-C-unique-terms" --rerank --top 5
```

**Critical rule**: each directed search must contain 4-5 terms from that source's own index/glossary, not generic synonyms. If a source has few chunks, it needs its own terms to surface.

### Step 3 — Extract and organize findings

For each retrieved passage, record: source filename, page number, relevance score, key idea (1 sentence), and how it connects to the main topic.

### Step 4 — Build the integrated model

Structure: WHAT (theoretical base) > HOW IT'S PERCEIVED (context) > HOW TO EXECUTE (operations).

Each source must appear at least twice. Connections between sources must be explicit.

### Step 5 — Write the Obsidian note

Structure with 7 sections:
1. **Introduction + source table** — 3-column table (Source | What it contributes | Why it matters)
2. **Short answer** — 2-3 paragraphs, bold conclusion
3. **Per-source breakdown** — One subsection per source with citations
4. **Integrated model** — ASCII diagram + narrated connections
5. **Action plan** — Numbered, actionable steps with source backing
6. **What to NEVER do** — Common mistakes with source justification
7. **Sources consulted** — All citations grouped by source

Citation format: `[Fuente: filename, Encabezado: "Section Title"]`

Write notes using `Out-File -Encoding UTF8` for special characters.

### Step 6 — Quality checklist

- [ ] At least one directed search per source
- [ ] Each source appears at least twice in the analysis
- [ ] Connections between sources are explicit
- [ ] ASCII diagram shows the integration model
- [ ] Every section has page-level citations
- [ ] Proper Spanish orthography (accents, n, inverted punctuation)
- [ ] Action plan has concrete steps

## What I need

- Library name (e.g., `marketing`)
- The central question/topic
- OpenAI API key (env var `OPENAI_API_KEY`) for LLM calls
- Vault path (from `config.json` or env `ATHENA_VAULT_PATH`) for writing notes

## Limitations

- I only use text indexed in the Ragthen library. Never external knowledge.
- If a source doesn't cover the topic directly, I extract implications from related concepts.
