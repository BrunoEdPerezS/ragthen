## Why

Raghten actualmente solo ingiere PDFs, TXTs y MDs. Los PDFs se procesan con PyMuPDF `get_text()`, que extrae texto plano sin estructura y corrompe ecuaciones matemáticas. Quedan excluidos formatos clave como EPUB, estándar en libros técnicos, académicos y documentación. Además, el chunking actual es ciego (ventana de 1200 caracteres) sin respetar la estructura semántica de los documentos, lo que degrada la calidad de los chunks y la precisión del retrieval.

## What Changes

- **Nuevo formato de entrada EPUB**: Se añade soporte para archivos `.epub` en el pipeline de ingestion. Los EPUBs se convierten en memoria a Markdown usando `ebooklib` + un convertidor XHTML→MD, preservando estructura de capítulos y metadatos.
- **Conversión MathML → LaTeX**: Durante la extracción de EPUBs, los elementos `<math>` con MathML se convierten a notación LaTeX para que el LLM (gpt-4o) pueda interpretar ecuaciones correctamente.
- **Chunking semántico para Markdown**: El chunking detecta headings de Markdown (`#`, `##`, `###`, etc.) y particiona el texto en secciones lógicas en lugar de ventanas ciegas de caracteres. Para contenido sin headings, mantiene el comportamiento actual (sliding window) como fallback.
- **Metadatos enriquecidos**: Los chunks originados de EPUBs incluyen información de capítulo/sección en sus metadatos, permitiendo citaciones más precisas (ej: `[Source: libro.epub, Cap 3 > Teorema de Bayes]`).

## Capabilities

### New Capabilities
- `epub-ingestion`: Ingesta de archivos EPUB mediante conversión en memoria a Markdown. Incluye extracción de XHTML por capítulo, conversión a MD, manejo de MathML→LaTeX, y extracción de metadatos (título del capítulo, autor del libro).
- `semantic-chunking`: Chunking consciente de la estructura para contenido Markdown. Detecta headings (`#`–`######`) y parte el texto en secciones lógicas. Si una sección excede `chunk_size`, aplica sub-chunking con sliding window. Para texto sin headings, conserva el comportamiento actual como fallback.

### Modified Capabilities
- `ragthen-core`: El requerimiento de Document Ingestion se expande para incluir archivos `.epub` en el glob de ingestion y dispatch a la nueva función de extracción. El comportamiento de chunking se extiende con modo heading-aware para contenido Markdown.

## Impact

- **Dependencias nuevas**: `ebooklib` (lectura de EPUB, puro Python), `html2text` o similar (conversión XHTML→MD)
- **Archivos afectados**:
  - `ragthen-core/src/ragthen_core/storage.py`: nuevas funciones `extract_epub_pages()`, mejoras en `chunk_pages()`
  - `ragthen-core/src/ragthen_core/engine.py`: modificación de `ingest()` para incluir `*.epub`
  - `ragthen-core/pyproject.toml`: nuevas dependencias
- **Sin breaking changes**: La API existente de `ingest()`, `search()`, `ask()` no cambia. Los PDFs, TXTs y MDs se procesan igual que antes.
- **Sin cambios en `ragthen-agent` ni `ragthen-content`**: El CLI y backends ya manejan la ingestion de forma genérica.
