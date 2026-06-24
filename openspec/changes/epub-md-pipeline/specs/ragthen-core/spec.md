# raghten-core (delta)

## Purpose
Delta spec for the raghten-core RAG engine. This change adds EPUB file support to document ingestion and extends chunking with heading-aware mode for Markdown content.

## MODIFIED Requirements

### Requirement: Document Ingestion
The system SHALL ingest PDF, EPUB, TXT, and MD files from a library directory into a ChromaDB collection. PDFs SHALL be parsed with PyMuPDF (fitz) extracting page-level text. EPUBs SHALL be parsed with ebooklib converting XHTML to Markdown per chapter. TXT and MD files SHALL be read directly. Text SHALL be chunked with configurable size and overlap, optionally using heading-aware splitting for Markdown content. Chunks SHALL be embedded using `all-MiniLM-L6-v2` via sentence-transformers and stored in ChromaDB with metadata (source filename, page number, optional section path).

#### Scenario: Library contains PDFs, EPUBs, TXTs, and MDs
- **WHEN** `ingest()` is called on a library directory containing a mix of file types (PDF, EPUB, TXT, MD)
- **THEN** all files are processed, each dispatched to its appropriate extraction function, and all text is chunked, embedded, and stored in the ChromaDB index with source and page metadata

#### Scenario: Library has no processable files
- **WHEN** `ingest()` is called on a directory with no PDF, EPUB, TXT, or MD files
- **THEN** the system prints a message indicating no files were found and returns without error

#### Scenario: PDF file has no extractable text
- **WHEN** a PDF yields empty text for all pages
- **THEN** the system skips that file with a message "(no extractable text, skipping)"

#### Scenario: EPUB file has no extractable text
- **WHEN** an EPUB yields empty text for all spine items
- **THEN** the system skips that file with a message "(no extractable text, skipping)"

#### Scenario: DRM-protected EPUB
- **WHEN** an EPUB file is DRM-protected and cannot be opened
- **THEN** the system skips that file with a message indicating DRM protection and continues processing other files

#### Scenario: Ingestion with heading-aware chunking
- **WHEN** `ingest()` processes Markdown content from EPUBs or MD files with `heading_aware=True`
- **THEN** chunks are created along heading boundaries, and chunk metadata includes an optional `section` field with the heading hierarchy

## ADDED Requirements

### Requirement: EPUB Dependency Availability
The system SHALL attempt to import `ebooklib` and `markdownify` at ingestion time. If either library is not installed, the system SHALL print a clear message indicating the missing dependency and skip EPUB processing without affecting other file formats.

#### Scenario: ebooklib not installed
- **WHEN** `ingest()` encounters an `.epub` file but `ebooklib` is not installed
- **THEN** the system prints "epub support requires ebooklib: pip install ebooklib" and skips the EPUB file

#### Scenario: Both EPUB dependencies available
- **WHEN** `ingest()` encounters an `.epub` file and both `ebooklib` and `markdownify` are importable
- **THEN** the EPUB is processed normally through `extract_epub_pages()`
