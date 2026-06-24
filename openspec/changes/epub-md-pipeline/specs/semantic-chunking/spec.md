# semantic-chunking

## Purpose
Chunking consciente de la estructura Markdown que detecta headings y particiona el texto en secciones lógicas, preservando contexto jerárquico en los metadatos de cada chunk.

## ADDED Requirements

### Requirement: Heading-Aware Chunk Splitting
The system SHALL detect Markdown headings (`# `, `## `, `### `, `#### `, `##### `, `###### `) at the start of lines and split text at heading boundaries before applying fixed-size chunking. Each heading SHALL define a new section boundary.

#### Scenario: Text with multiple headings
- **WHEN** `chunk_pages()` receives a page with text containing `## Intro\ncontent...\n## Methods\nmore content...` and `heading_aware=True`
- **THEN** the text is split into at least two sections: one starting with `## Intro` and its content, another starting with `## Methods` and its content

#### Scenario: Text with nested headings
- **WHEN** a page contains `# Part 1\n## Chapter 1\ntext...\n## Chapter 2\ntext...`
- **THEN** sections are created at each heading level, maintaining the hierarchy in metadata (e.g., `section: "Part 1 > Chapter 1"`)

#### Scenario: Text without headings
- **WHEN** a page contains text with no Markdown headings at line start and `heading_aware=True`
- **THEN** the system falls back to the default sliding-window chunking behavior (identical to `heading_aware=False`)

#### Scenario: Heading inside code block
- **WHEN** a page contains a fenced code block with `# comment` inside and `heading_aware=True`
- **THEN** the `# comment` inside the code block is NOT treated as a section boundary

### Requirement: Section Sub-Chunking for Large Content
The system SHALL apply sliding-window sub-chunking to sections whose text length exceeds `chunk_size`, using the same `chunk_size` and `chunk_overlap` parameters as the base chunking.

#### Scenario: Section fits within chunk_size
- **WHEN** a section's text is shorter than `chunk_size`
- **THEN** the entire section becomes a single chunk with the section's heading context in metadata

#### Scenario: Section exceeds chunk_size
- **WHEN** a section's text is longer than `chunk_size`
- **THEN** the section is split into multiple overlapping chunks using the sliding-window algorithm, and all chunks share the same section metadata

### Requirement: Section Metadata in Chunks
The system SHALL include an optional `section` field in chunk metadata containing the hierarchical path of headings that led to the chunk.

#### Scenario: Single-level heading
- **WHEN** a chunk comes from a section under `## Methods`
- **THEN** the chunk metadata includes `"section": "Methods"`

#### Scenario: Nested headings
- **WHEN** a chunk comes from a section under `# Results > ## Analysis > ### Statistical Tests`
- **THEN** the chunk metadata includes `"section": "Results > Analysis > Statistical Tests"`

#### Scenario: Chunk from heading-free text
- **WHEN** a chunk comes from text without any headings
- **THEN** the `section` field is absent from the chunk metadata

### Requirement: Backward Compatibility
The system SHALL maintain the existing behavior when `heading_aware=False` or when the parameter is not provided (defaulting to current sliding-window behavior).

#### Scenario: heading_aware=False
- **WHEN** `chunk_pages()` is called with `heading_aware=False`
- **THEN** the chunking behaves identically to the current implementation (pure sliding window across the full page text)

#### Scenario: Default behavior preserved
- **WHEN** `chunk_pages()` is called with only `pages`, `chunk_size`, and `chunk_overlap` (no `heading_aware` argument)
- **THEN** `heading_aware` defaults to `False` and the current sliding-window behavior is used
