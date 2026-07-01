# RAG_Iniciativa

## Introducción

**Ragthen** es un sistema RAG (Retrieval-Augmented Generation) local-first, diseñado para consultar librerías académicas extensas — predominantemente PDFs — desde un agente de OpenCode. Su arquitectura se basa en tres principios:

1. **Library-first**: Todas las respuestas provienen exclusivamente de los documentos indexados. Conocimiento externo cero (no web search, no web fetch).
2. **Separation of Concerns**: Ragthen es un agente de solo lectura. Investiga, recupera contexto con citas, y devuelve hallazgos al agente principal (Plan/Build), que decide qué hacer con la información.
3. **Local-first, remote-ready**: Opera localmente con ChromaDB + sentence-transformers (sin red), y tiene previsto un backend remoto para exponer una API/MCP server.

### Arquitectura actual

```
PDFs / EPUBs / TXTs / MDs
        │
        ▼
┌──────────────────┐     ┌─────────────┐     ┌──────────────────┐
│  ragthen-core    │────▶│  ChromaDB   │◀────│  ragthen-agent   │
│  (engine RAG)    │     │  (Persist.) │     │  (CLI + backends)│
└──────────────────┘     └─────────────┘     └────────┬─────────┘
                                                      │
                              ┌───────────────────────┘
                              ▼
                     ┌──────────────┐
                     │  OpenCode    │
                     │  Agent       │
                     │  (Ragthen.md)│
                     └──────────────┘
```

**Stack**: ChromaDB (vector store), PyMuPDF (extracción PDF), ebooklib + markdownify (extracción EPUB), sentence-transformers (embeddings all-MiniLM-L6-v2 + reranker ms-marco-MiniLM-L-6-v2), OpenAI (ragthen ask).

---

## Problemas

### Problema raíz: La calidad de ingesta desde PDF es deficiente

La mayoría de los recursos académicos del usuario son libros en formato PDF. El pipeline actual de PDF usa `PyMuPDF` (`fitz`) con `page.get_text()` — el extractor más básico posible. Esto genera los siguientes fallos documentados:

| Problema | Impacto | Evidencia |
|----------|---------|-----------|
| **PDFs escaneados → cero chunks** | Libros enteros invisibles para el sistema sin warning | Meadows - Thinking in Systems (Systhink) |
| **Encoding corrupto** | Acentos, ñ, caracteres especiales → `?` | Kotler - Fundamentos del Marketing (Retsell) |
| **Layout complejo mezclado** | Tablas, columnas, TOC, índices, referencias entran como texto continuo | Sterman - Business Dynamics: 70+ págs de TOC/index contaminando |
| **Headers/footers en contenido** | Números de página, encabezados repetitivos contaminan chunks |
| **Chunking ciego por caracteres** | Ventana deslizante de 1200 chars corta palabras y oraciones a la mitad, sin respetar estructura semántica |
| **Modelo de embeddings truncado** | all-MiniLM-L6-v2 (256 tokens máx) trunca chunks largos silenciosamente |
| **Sin paralelismo** | Ingesta secuencial, lenta con documentos grandes |

### Problema derivado: El pipeline EPUB no es viable

El pipeline EPUB (ebooklib + markdownify + chunking semántico heading-aware + MathML→LaTeX) es muy superior: preserva estructura de capítulos, detecta headings, convierte fórmulas. Pero **no es viable porque casi ningún recurso académico está en formato EPUB**.

### Problema estratégico: Sin servidor remoto

Ragthen tiene un `RemoteBackend` (cliente HTTP) pero **no existe implementación del servidor**. No hay FastAPI, no hay MCP server. El usuario está montando un miniserver y necesita acceso remoto desde internet.

### Problema de experiencia: notebooklm-py no es la solución

Se exploró `notebooklm-py` como alternativa. Ventajas: OCR por Google Vision, encoding perfecto, chunking semántico vía LLM, formatos ilimitados. Desventajas críticas: API no oficial de Google (puede romperse), datos en servidores de Google, dependencia de internet, no integrable con OpenCode.

---

## Posibles soluciones

### Opción A: Mejorar el pipeline PDF de Ragthen (conservador)

Reemplazar o complementar PyMuPDF con herramientas más robustas, preservando la arquitectura actual.

**Acciones concretas**:
- **Preprocesamiento con OCRmyPDF**: Pasar PDFs escaneados por OCR antes de ingestar
- **Cambiar extractor**: Evaluar `pdfplumber` (mejor para tablas/layout), `pymupdf4llm` (Markdown-aware), `marker-pdf` (modelo DETR para layout)
- **Mejorar chunking**: Implementar chunking semántico también para PDFs (detección de headings, secciones)
- **Mejor modelo de embeddings**: Migrar a `all-mpnet-base-v2` (768d, 512 tokens) o modelos multilingües
- **Paralelizar ingesta**: `multiprocessing` o `asyncio` para procesar múltiples PDFs simultáneamente

**Ventajas**: Cambio incremental, preserva inversión en Ragthen, sin dependencias externas.
**Desventajas**: Sigue siendo un sistema de extracción de texto de PDFs — los PDFs mal formateados siempre serán problemáticos. Requiere desarrollo significativo.

### Opción B: Reemplazar Ragthen con LlamaIndex

Migrar los módulos de ingesta, chunking, embedding y búsqueda a LlamaIndex, manteniendo la capa de agente/CLI de Ragthen.

**Lo que LlamaIndex aporta**:
- `SimpleDirectoryReader` con soporte para múltiples formatos (PDF, DOCX, EPUB, Markdown, etc.)
- `IngestionPipeline` con transformaciones modulares (chunking semántico, extracción de metadatos, etc.)
- `SentenceSplitter` con chunking por tokens (no caracteres), respetando oraciones
- Integración nativa con ChromaDB, múltiples modelos de embedding, rerankers
- Modo server/service para exponer como API
- Framework maduro con comunidad activa

**Acciones concretas**:
- Reemplazar `ragthen-core/storage.py` con `SimpleDirectoryReader` + `IngestionPipeline`
- Reemplazar `ragthen-core/engine.py` con `VectorStoreIndex` de LlamaIndex
- Mantener `ragthen-agent` como CLI wrapper sobre LlamaIndex
- Exponer API vía `llama-index-server` o FastAPI sobre el índice

**Ventajas**: Menos código que mantener, se delega el pipeline a un framework probado, actualizaciones automáticas, comunidad grande, modo servidor incorporado.
**Desventajas**: Dependencia externa pesada, pérdida de control sobre el pipeline, overhead de abstracción, posible incompatibilidad con la arquitectura de backends actual.

### Opción C: Reemplazar Ragthen con Khoj

Khoj es una alternativa open-source de RAG que funciona como agente personal con soporte para múltiples formatos (PDF, Markdown, GitHub, Notion, etc.) e incluye servidor web, API, Obsidian plugin y chat.

**Lo que Khoj aporta**:
- Servidor web + API REST + MCP server (nativo o por plugin) listos para usar
- Agentes de chat con múltiples modelos (OpenAI, Anthropic, Ollama, locales)
- Procesamiento de PDFs con OCR (usa `pymupdf` + tesseract, pero con pipeline más pulido)
- Chunking semántico
- Búsqueda híbrida (BM25 + embeddings)
- Obsidian plugin para indexar vaults automáticamente
- Docker ready, autohosted
- Comunidad activa (25k+ stars)

**Acciones concretas**:
- Desplegar Khoj en el miniserver con Docker
- Configurar carpetas de librerías como fuentes de datos
- Exponer API/MCP server desde el miniserver
- Conectar OpenCode al MCP server de Khoj (o a su API REST)

**Ventajas**: Menos desarrollo (producto terminado), API/MCP server out-of-the-box, OCR integrado, búsqueda híbrida, Obsidian integration, comunidad grande.
**Desventajas**: Pérdida total del trabajo hecho en Ragthen, menos control sobre el comportamiento del agente, curva de configuración, posible sobrecarga para el miniserver.

### Opción D: Pipeline híbrido (preprocesamiento + Ragthen)

Crear un pipeline de preprocesamiento de PDFs que convierta cada documento a Markdown de alta calidad antes de ingestar en Ragthen, aprovechando que Ragthen ya tiene chunking semántico para Markdown.

**Acciones concretas**:
- Usar `pymupdf4llm` o `marker-pdf` para convertir PDF → Markdown estructurado
- Almacenar los `.md` resultantes en la librería junto al PDF
- Ingestar los `.md` en Ragthen (el pipeline MD ya usa chunking semántico)
- Opcional: conservar el PDF original para citas de página exacta

**Ventajas**: Aprovecha lo mejor de ambos mundos — conversión de calidad + arquitectura existente de Ragthen. Menos cambios en el código base.
**Desventajas**: Paso extra en el workflow, duplicación de archivos, dependencia de herramientas externas de conversión.

### Opción E: Implementar API/MCP server en Ragthen (independiente)

Implementar el servidor que falta en Ragthen usando FastAPI + MCP SDK de Anthropic, independientemente de qué solución de ingesta se adopte.

**Acciones concretas**:
- Crear `ragthen-server` como paquete nuevo en el monorepo
- FastAPI para endpoints REST (`/ingest`, `/search`, `/ask`, `/status`, `/clear`)
- MCP server (usando `mcp` SDK) para integración directa con OpenCode/clients MCP
- Autenticación básica (API key)
- Dockerfile para despliegue en miniserver

**Ventajas**: Independiza la decisión de ingesta de la de servidor. Se puede construir ya.
**Desventajas**: Requiere mantener el servidor como pieza adicional.

---

## Conclusión

### Diagnóstico

Ragthen resuelve bien el problema de *consultar información con un agente de OpenCode* (SOC, permisos, flujo de trabajo). Donde falla es en *aprovechar librerías PDF extensas*: la extracción de texto de PDFs con PyMuPDF básico genera chunks de baja calidad que degradan todo el pipeline downstream (embeddings imprecisos, búsqueda deficiente, respuestas pobres).

El pipeline EPUB demostró que con buena extracción + chunking semántico el sistema funciona. El problema no es Ragthen como arquitectura, es el extractor de PDF.

### Curso de acción recomendado

Se recomienda un enfoque en **dos frentes simultáneos**:

**Frente 1 — Preprocesamiento (corto plazo, alto impacto):**
Adoptar la **Opción D (pipeline híbrido)**. Usar `pymupdf4llm` o `marker-pdf` para convertir PDFs a Markdown estructurado antes de ingestar. Esto resuelve el problema de calidad de extracción sin reescribir Ragthen, y aprovecha el chunking semántico que ya existe para Markdown.

**Frente 2 — Servidor (medio plazo, habilitante):**
Implementar la **Opción E (API/MCP server)**. Crear un servidor FastAPI + MCP para Ragthen que permita acceso remoto desde internet. Esto habilita el miniserver y desbloquea el backend remoto que ya tiene el cliente preparado.

**Si el Frente 1 no da resultados satisfactorios**, escalar a la **Opción B (LlamaIndex)** como reemplazo del motor de ingesta/búsqueda, manteniendo el agente y CLI de Ragthen. Khoj (Opción C) queda como último recurso si se prefiere abandonar el desarrollo propio y adoptar una solución completa.

### Próximos pasos inmediatos

1. Probar `pymupdf4llm` con 2-3 PDFs problemáticos (uno escaneado, uno con encoding corrupto, uno con layout complejo) y evaluar calidad del Markdown resultante.
2. Si la calidad es buena, implementar el pipeline de conversión PDF→MD automatizado en el flujo de ingesta.
3. Paralelamente, iniciar el desarrollo de `ragthen-server` con FastAPI + MCP SDK.
4. Documentar resultados y reevaluar en una semana.
