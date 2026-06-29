# Resumen: Evaluación de librerías Ragthen y alternativas

## Fecha
2026-06-29

## Contexto
Se ingirieron 3 librerías en Ragthen (Retsell, Systhink → Thinksight) y se evaluó la calidad de extracción de texto desde PDFs. Luego se exploró NotebookLM como alternativa vía `notebooklm-py`.

---

## Librerías evaluadas

### Retsell (5,500 chunks)
| Documento | Calidad | Observaciones |
|-----------|---------|---------------|
| Kotler - Fundamentos del Marketing | ✅ Excelente | Acentos → `?` por encoding de PyMuPDF |
| Kotler - Marketing 4.0 | ✅ Excelente | Mismo encoding problemático |
| Sapag - Evaluación de Proyectos | ✅ Excelente | Fórmulas legibles, acentos corruptos |
| Roberge - Sales Acceleration Formula | ✅ Bien | Contenido real recuperable con queries específicas |

### Systhink (3,144 chunks) → Reemplazada por Thinksight
| Documento | Calidad | Observaciones |
|-----------|---------|---------------|
| Anderson - Systems Thinking Basics | ✅ Excelente | Mejor extraído de todos |
| Meadows - Thinking in Systems | ❌ Mala | PDF escaneado sin capa de texto — cero resultados |
| Sterman - Business Dynamics | ⚠️ Regular | Contenido real extraído pero sepultado por 70+ páginas de TOC/index/referencias |

### Thinksight (2,437 chunks) — Estado final
| Documento | Calidad | Relevancia |
|-----------|---------|------------|
| Anderson - Systems Thinking Basics | ✅ Excelente | 0.98 – 0.99 |
| Newman - Networks | ✅ Excelente | 0.63 – 0.99 |

---

## Problemas detectados en Ragthen (código fuente analizado)

Ragthen usa `PyMuPDF` con `page.get_text()` — el extractor más básico posible:

1. **Sin OCR** — PDFs escaneados producen cero chunks sin advertencia
2. **Sin análisis de layout** — tablas, columnas múltiples, índices → texto mezclado
3. **Sin limpieza de encoding** — caracteres no-ASCII se corrompen (acentos → `?`)
4. **Sin detección de headers/footers** — números de página, encabezados repetitivos entran al contenido
5. **Chunking por caracteres (1200)** — corta palabras/oraciones, no respeta semántica
6. **Modelo de embeddings limitado** — all-MiniLM-L6-v2 (384 dims, 256 tokens máx) trunca chunks largos silenciosamente
7. **Chunks sin cruzar páginas** — contenido partido entre páginas pierde continuidad
8. **Sin paralelismo** — ingesta secuencial, lenta con documentos grandes

### Pipeline EPUB (mucho mejor)
- Usa `ebooklib` + `markdownify` + convertidor MathML → LaTeX
- Chunking heading-aware: respeta secciones del documento
- DRM detection
- El problema es que ninguna librería actual usa EPUBs

---

## Alternativa: notebooklm-py

### ¿Qué es?
Wrapper Python sobre los endpoints no documentados de Google NotebookLM. **NO es local** — los PDFs se suben a Google Cloud.

### Comparativa vs Ragthen

| Aspecto | Ragthen | notebooklm-py |
|---------|---------|---------------|
| Procesamiento | Local | Google Cloud |
| OCR en escaneados | ❌ | ✅ Google Vision |
| Encoding/acentos | ⚠️ Corrupto | ✅ Perfecto |
| Layout complejo | ❌ | ✅ Pipeline Google Docs |
| Embeddings | all-MiniLM-L6-v2 (384d) | Gemini (propietario) |
| Chunking | Por caracteres | Semántico (LLM) |
| Offline | ✅ Sí | ❌ No |
| Formatos | PDF, EPUB, TXT, MD | PDF, EPUB, Word, audio, video, imágenes, YouTube, URLs, Drive |
| Generación contenido | ❌ | ✅ Podcasts, videos, quizzes, flashcards, mind maps |
| Dependencia externa | Ninguna | Google APIs no oficiales (pueden romperse) |
| Privacidad | Total | Tus datos van a Google |

### Instalación
```bash
uv tool install "notebooklm-py[browser]"
notebooklm login
notebooklm create "Mi librería"
notebooklm source add ./documento.pdf
notebooklm ask "¿Qué dice sobre X?"
```

### Desde Python
```python
from notebooklm import NotebookLMClient

async with NotebookLMClient.from_storage() as client:
    nb = await client.notebooks.create("Thinksight")
    await client.sources.add_file(nb.id, "documento.pdf")
    res = await client.chat.ask(nb.id, "Resume esto")
    print(res.answer)
```

### Riesgos
- API no documentada de Google — puede cambiar sin aviso
- Rate limits
- Dependencia de conexión a internet
- Tus documentos se almacenan en servidores de Google

---

## Recomendación

**Usar ambos, no elegir uno:**

- **Ragthen** → para consultas rápidas, offline, control de datos, workflows automatizados locales
- **notebooklm-py** → para análisis profundos donde se necesita calidad Google (OCR, encoding, layout complejo)

No son mutuamente excluyentes. Una misma biblioteca de PDFs puede existir como librería Ragthen y como notebook en NotebookLM.

### Para mejorar Ragthen sin cambiar de herramienta
- Pasar PDFs escaneados por OCRmyPDF antes de ingerir
- Usar un mejor modelo de embeddings (si Ragthen lo soporta)
- Convertir PDFs problemáticos a EPUB (el pipeline EPUB es muy superior)
