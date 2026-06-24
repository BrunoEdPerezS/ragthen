## 1. Dependencies

- [ ] 1.1 Add `ebooklib` to `ragthen-core/pyproject.toml` dependencies
- [ ] 1.2 Add `markdownify` to `ragthen-core/pyproject.toml` dependencies
- [ ] 1.3 Run `pip install -e raghten-core` to verify dependency resolution

## 2. EPUB Extraction

- [ ] 2.1 Implement `extract_epub_pages(filepath)` in `ragthen-core/src/ragthen_core/storage.py`
- [ ] 2.2 Handle DRM-protected EPUBs with a clear message and empty return
- [ ] 2.3 Handle malformed or corrupt EPUBs without crashing
- [ ] 2.4 Extract chapter title from first heading or manifest title per spine item
- [ ] 2.5 Handle lazy imports: print "epub support requires ebooklib: pip install ebooklib" if ebooklib is not installed

## 3. XHTML to Markdown Conversion

- [ ] 3.1 Configure `markdownify` with heading support (h1-h6), paragraphs, lists, links, emphasis, code blocks
- [ ] 3.2 Strip non-content XHTML elements (scripts, styles, nav, metadata)

## 4. MathML to LaTeX Conversion

- [ ] 4.1 Create a `markdownify` CustomConverter that intercepts `<math>` tags
- [ ] 4.2 Implement MathML to LaTeX conversion for common equation patterns (identifiers, operators, fractions, superscripts, subscripts, sums, integrals)
- [ ] 4.3 Fallback to alttext attribute or `[equation]` placeholder for unparseable MathML
- [ ] 4.4 Distinguish inline vs block equations based on `display` attribute

## 5. Semantic Chunking

- [ ] 5.1 Add `heading_aware: bool = False` parameter to `chunk_pages()` in `ragthen-core/src/ragthen_core/storage.py`
- [ ] 5.2 Implement heading detection via regex `^(#{1,6})\s+` at line start (excluding lines inside fenced code blocks)
- [ ] 5.3 Implement section splitting at heading boundaries with hierarchical path tracking
- [ ] 5.4 Implement sub-chunking fallback for sections exceeding `chunk_size` using existing sliding-window logic
- [ ] 5.5 Add optional `section` field to chunk metadata with heading hierarchy (e.g., `"Part 1 > Chapter 2 > Methods"`)
- [ ] 5.6 Verify backward compatibility: `heading_aware=False` behaves identically to current implementation

## 6. Engine Integration

- [ ] 6.1 Add `*.epub` glob to `ingest()` in `ragthen-core/src/ragthen_core/engine.py`
- [ ] 6.2 Add EPUB dispatch in the file processing loop (`if .epub: extract_epub_pages()`)
- [ ] 6.3 Update `ingest()` log message to include EPUB count
- [ ] 6.4 Pass `heading_aware=True` when chunking EPUB and MD content
- [ ] 6.5 Update `resolve_library()` help message to mention EPUB files

## 7. Verification

- [ ] 7.1 Create a test library with a sample EPUB (no DRM) and run `ragthen ingest -l <lib>` to verify ingestion
- [ ] 7.2 Run `ragthen status -l <lib>` and confirm EPUB chunks appear with section metadata
- [ ] 7.3 Run `ragthen search -l <lib> "query" --rerank` and verify results include EPUB sources
- [ ] 7.4 Verify backward compatibility: ingest a PDF-only library and confirm no regressions
- [ ] 7.5 Test with EPUB containing MathML equations and verify `$...$` LaTeX output in chunks
- [ ] 7.6 Test with DRM-protected EPUB and verify graceful handling
