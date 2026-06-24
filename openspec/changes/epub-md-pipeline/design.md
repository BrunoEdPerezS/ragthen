## Context

Raghten actualmente ingiere PDFs via PyMuPDF (texto plano), y TXTs/MDs via lectura directa. El chunking es ciego: ventana deslizante de `chunk_size` caracteres con `chunk_overlap`, sin considerar estructura del documento. Esto tiene dos consecuencias: (1) formatos ricos como EPUB quedan fuera, y (2) los chunks pueden cortar mitad de una oración, una ecuación, o mezclar secciones no relacionadas.

Este cambio añade dos capacidades: ingesta de EPUB con conversión en memoria a Markdown, y chunking consciente de la estructura Markdown (headings). Ambas son independientes pero se complementan: un EPUB convertido a MD se beneficia directamente del chunking semántico.

## Goals / Non-Goals

**Goals:**
- Soportar archivos `.epub` como formato de entrada en `ragthen ingest`
- Convertir EPUB en memoria (sin archivos intermedios) a Markdown estructurado
- Preservar estructura de capítulos y metadatos del EPUB
- Convertir ecuaciones MathML a notación LaTeX durante la extracción
- Implementar chunking heading-aware para contenido Markdown
- Mantener total backward compatibility: PDFs, TXTs y MDs existentes sin cambios

**Non-Goals:**
- No se modifica la extracción de PDFs (PyMuPDF `get_text()` sigue igual)
- No se cambia el modelo de embeddings (`all-MiniLM-L6-v2`)
- No se añade OCR para PDFs escaneados ni EPUBs con imágenes
- No se modifica la API de `search()`, `ask()`, ni el CLI
- No se implementa chunking semántico para PDFs (solo para MD)
- No se añade semantic chunking por párrafos o tópicos (solo headings)

## Decisions

### D1: `ebooklib` para lectura de EPUB

**Alternativas consideradas:**
- `pandoc` (subprocess): mejor calidad de conversión, especialmente tablas complejas. Pero requiere instalación externa en el sistema (no `pip install`), rompe la filosofía self-contained del proyecto.
- `epub2txt`: muy básico, no maneja estructura.
- `EbookLib` + conversor XHTML→MD: 100% Python, `pip install`, sin dependencias de sistema. Calidad suficiente para el caso de uso (texto + ecuaciones + headings).

**Decisión:** `ebooklib` para leer el EPUB y acceder a los items del spine, combinado con `markdownify` para convertir XHTML a Markdown. `markdownify` maneja headings, listas, links, code blocks, y permite customizar el manejo de tags (clave para MathML).

### D2: `markdownify` sobre `html2text`

**Alternativas consideradas:**
- `html2text`: sólido pero difícil de extender para manejo custom de tags `<math>`.
- `markdownify`: API más flexible, permite definir convertidores por tag via `CustomConverter`. Esto es crítico para interceptar `<math>` y convertirlo a LaTeX antes de que llegue al conversor genérico.

**Decisión:** `markdownify` con un `CustomConverter` para tags `<math>`. Esto permite inyectar lógica MathML→LaTeX sin modificar la librería.

### D3: Conversión MathML → LaTeX inline

**Estrategia:** Durante la extracción de XHTML de cada item del EPUB, se detectan elementos `<math>` con contenido MathML. Se aplica conversión MathML→LaTeX y el resultado se inserta como `$...$` (inline) o `$$...$$` (block) dentro del Markdown.

**Alternativa considerada:** Dejar MathML como HTML crudo en el MD. Esto es más simple pero el LLM no interpreta MathML nativamente; prefiere LaTeX.

**Decisión:** Conversión a LaTeX. Si la conversión falla (MathML malformado), se preserva el texto alternativo del `<math>` si existe (`alttext`), o se omite la ecuación con un marcador `[ecuación]`.

### D4: Estructura de metadata para EPUB

Cada item del spine del EPUB se mapea a una "página" lógica:

```python
{
    "text": "...",           # MD convertido
    "page": N,               # número secuencial (orden del spine)
    "source": filepath.name, # ej: "libro.epub"
    "chapter_title": "...",  # título del capítulo/sección
    "type": "epub"           # discrimina PDF de EPUB
}
```

El campo `chapter_title` se extrae del primer heading (`<h1>`–`<h6>`) encontrado en el XHTML, o del `title` del item en el manifest.

### D5: Chunking heading-aware

**Algoritmo:**
1. Si el texto de una "página" contiene headings Markdown (`# `, `## `, ..., `###### `), se particiona en los puntos de heading.
2. Cada sección resultante hereda el contexto de su heading (ej: `## Teorema de Bayes`).
3. Si una sección excede `chunk_size`, se aplica sub-chunking con sliding window (comportamiento actual como fallback).
4. Si el texto no contiene headings, se aplica directamente el sliding window actual.
5. Los metadatos del chunk incluyen `section` opcional con la jerarquía de headings (ej: `"Cap 3 > Teorema de Bayes"`).

**Decisión:** Modificar `chunk_pages()` en `storage.py` para que acepte un parámetro opcional `heading_aware: bool = True`. Cuando es `True`, aplica el algoritmo descrito. Esto mantiene la firma actual compatible.

### D6: Dispatch en ingestion

En `engine.ingest()`, se añade `epub_files = list(library_dir.glob("*.epub"))` y en el loop de procesamiento:

```python
if filepath.suffix.lower() == ".pdf":
    pages = extract_pdf_pages(filepath)
elif filepath.suffix.lower() == ".epub":
    pages = extract_epub_pages(filepath)
else:
    pages = extract_text_file(filepath)
```

Esto mantiene la estructura de dispatch simple y extensible a futuros formatos.

## Risks / Trade-offs

- **[Riesgo] EPUB con contenido solo-imagen (cómics, scanned books):** `ebooklib` extrae XHTML; si el EPUB no tiene texto extraíble, `extract_epub_pages()` devolverá lista vacía. → **Mitigación:** Se imprime "(no extractable text, skipping)" igual que con PDFs sin texto.

- **[Riesgo] EPUBs con DRM:** `ebooklib` no puede leer EPUBs con DRM (Adobe DRM, Apple FairPlay). → **Mitigación:** Se captura la excepción y se imprime un mensaje claro: `"Cannot read DRM-protected EPUB: {filename}"`.

- **[Riesgo] MathML → LaTeX con pérdida de fidelidad:** La conversión de MathML a LaTeX no es perfecta; ecuaciones muy complejas (matrices anidadas, notación especial) pueden perder formato. → **Mitigación:** El texto alternativo del `<math>` se preserva como fallback. El LLM (gpt-4o) puede reconstruir ecuaciones a partir de LaTeX parcial.

- **[Riesgo] Chunking heading-aware en MD mal formateado:** Si un MD usa `#` dentro de bloques de código o texto, se interpretarán erróneamente como headings. → **Mitigación:** El split solo reconoce headings al inicio de línea (`^#{1,6}\s`). Esto minimiza falsos positivos. Los bloques de código (indentados o con backticks) no activan el split.

- **[Trade-off] ebooklib carga el EPUB completo en memoria:** Para EPUBs muy grandes (>100MB, libros de referencia), esto puede consumir memoria significativa. → **Aceptado:** El caso de uso típico es libros técnicos (<20MB). Si escala, se puede añadir streaming en el futuro.

- **[Trade-off] Chunking semántico solo para MD:** Los PDFs mantienen chunking ciego porque PyMuPDF no preserva estructura. → **Aceptado:** Mejorar extracción de PDFs es un cambio separado (ej: `page.get_text("markdown")` de PyMuPDF 1.23+).

## Open Questions

- **¿Manejar EPUBs con múltiples niveles de TOC?** Algunos EPUBs tienen tabla de contenidos anidada (Parte > Capítulo > Sección). La metadata actual captura solo el primer heading. Dejar capacidad de jerarquía para futura iteración.
- **¿Índice separado para ecuaciones?** Con MathML→LaTeX, se podría indexar ecuaciones en una colección separada con un modelo especializado en matemáticas. Fuera de scope para este cambio.
