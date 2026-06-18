# Ragthen Content

Este repositorio contiene la estructura de bibliotecas para Ragthen.
Los PDFs **NO** se versionan en Git.

## Estructura

```
libraries/
  <nombre-de-biblioteca>/
    libro1.pdf        ← Tus PDFs (ignorados por Git)
    libro2.pdf
    .index/           ← ChromaDB (generado, ignorado por Git)
```

## Cómo usar

1. Crea una carpeta por biblioteca dentro de `~/.ragthen/libraries/`:
   ```
   ~/.ragthen/libraries/marketing/
   ```

2. Coloca tus PDFs dentro de cada carpeta.

3. Ejecuta ingest:
   ```bash
   ragthen ingest -l marketing
   ```

4. Busca:
   ```bash
   ragthen search -l marketing "tu consulta"
   ```

## Sincronización desde Drive (futuro)

Usa `scripts/sync_from_drive.py` para descargar PDFs desde Google Drive
directamente a tus carpetas de biblioteca local.
