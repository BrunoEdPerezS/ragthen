# epub-ingestion

## Purpose
Ingesta de archivos EPUB mediante conversión en memoria a Markdown estructurado, preservando capítulos, metadatos y ecuaciones matemáticas.

## ADDED Requirements

### Requirement: EPUB Extraction
The system SHALL extract text from EPUB files using `ebooklib`, converting each spine item's XHTML content to Markdown via `markdownify`. Each spine item SHALL be treated as one logical page with chapter-level metadata.

#### Scenario: Valid EPUB with multiple chapters
- **WHEN** `extract_epub_pages()` is called with a valid EPUB file containing N spine items with text content
- **THEN** a list of N dicts is returned, each containing `text` (Markdown), `page` (sequential spine index starting at 1), `source` (filename), `chapter_title` (first heading text found in the item), and `type` ("epub")

#### Scenario: EPUB with no extractable text
- **WHEN** `extract_epub_pages()` is called with an EPUB where all spine items yield empty text after conversion
- **THEN** an empty list is returned

#### Scenario: EPUB with DRM protection
- **WHEN** `extract_epub_pages()` is called with a DRM-protected EPUB that ebooklib cannot open
- **THEN** the system prints a message indicating the EPUB is DRM-protected and returns an empty list without crashing

#### Scenario: Malformed EPUB
- **WHEN** `extract_epub_pages()` is called with a file that is not a valid EPUB
- **THEN** the system prints a warning to stderr and returns an empty list

### Requirement: XHTML to Markdown Conversion
The system SHALL convert each spine item's XHTML body to Markdown using `markdownify`, preserving headings (`h1`–`h6`), paragraphs, lists, links, emphasis (bold/italic), and code blocks.

#### Scenario: XHTML with headings and paragraphs
- **WHEN** a spine item contains `<h1>Title</h1><p>Text</p>`
- **THEN** the output Markdown is `# Title\n\nText`

#### Scenario: XHTML with lists
- **WHEN** a spine item contains `<ul><li>A</li><li>B</li></ul>`
- **THEN** the output Markdown contains `- A\n- B`

#### Scenario: XHTML with code blocks
- **WHEN** a spine item contains `<pre><code>print("hello")</code></pre>`
- **THEN** the output Markdown contains a fenced code block

### Requirement: MathML to LaTeX Conversion
The system SHALL detect `<math>` elements in XHTML content and convert MathML to LaTeX notation. Inline equations SHALL be wrapped in `$...$` and block equations in `$$...$$`.

#### Scenario: Inline MathML equation
- **WHEN** a spine item contains `<math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math>`
- **THEN** the output Markdown contains `$E = mc^{2}$`

#### Scenario: Block MathML equation
- **WHEN** a spine item contains `<math display="block">...</math>`
- **THEN** the output Markdown contains `$$...$$`

#### Scenario: Malformed MathML
- **WHEN** a `<math>` element contains invalid or unparseable MathML
- **THEN** the system inserts the alttext attribute content if present, otherwise inserts a placeholder `[equation]`

#### Scenario: No math elements
- **WHEN** an EPUB spine item contains no `<math>` elements
- **THEN** the Markdown conversion proceeds without modification

### Requirement: Chapter Title Extraction
The system SHALL extract the chapter title from each spine item by finding the first heading element (`h1`–`h6`) in the XHTML, or by reading the item's `title` attribute from the EPUB manifest if no heading is found.

#### Scenario: Item has h1 heading
- **WHEN** a spine item's XHTML begins with `<h1>Chapter 3: Methods</h1>`
- **THEN** the `chapter_title` field is set to "Chapter 3: Methods"

#### Scenario: Item has nested headings
- **WHEN** a spine item contains `<h2>Section 3.1</h2>` before any `h1`
- **THEN** the `chapter_title` field is set to "Section 3.1"

#### Scenario: Item has no heading but manifest title
- **WHEN** a spine item has no heading elements but the EPUB manifest defines a title for that item
- **THEN** the `chapter_title` field is set to the manifest title

#### Scenario: Item has no heading and no manifest title
- **WHEN** a spine item has no heading and no manifest title
- **THEN** the `chapter_title` field is set to an empty string

### Requirement: EPUB Ingestion in Engine
The system SHALL recognize `.epub` files during `ingest()` and process them using `extract_epub_pages()`, following the same chunking and embedding pipeline used for PDFs and text files.

#### Scenario: Library contains EPUB files
- **WHEN** `ingest()` is called on a library directory containing `.epub` files
- **THEN** EPUB files are processed, their text extracted via `extract_epub_pages()`, chunked, embedded, and stored in ChromaDB with source, page, and section metadata

#### Scenario: Library has EPUB alongside PDFs and MDs
- **WHEN** `ingest()` is called on a library with a mix of `.epub`, `.pdf`, `.txt`, and `.md` files
- **THEN** all formats are processed correctly, each dispatched to the appropriate extraction function
