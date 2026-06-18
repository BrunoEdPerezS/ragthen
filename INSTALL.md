# Ragthen — Instalacion

## Requisitos

- Python 3.10+
- Git (para instalacion desde repo)
- [opencode](https://opencode.ai) (para usar el agente)

## Instalacion rapida (Windows PowerShell)

```powershell
# 1. Clonar el repo
git clone <repo-url> Ragthen
cd Ragthen

# 2. Ejecutar bootstrap (instala ambos paquetes + configura)
.\ragthen-agent\bootstrap.ps1

# 3. Copiar agente y skill a la config de opencode
& "$env:APPDATA\Python\Python313\Scripts\ragthen.exe" setup
```

## Instalacion manual

### 1. Instalar dependencias

```powershell
pip install chromadb pymupdf sentence-transformers openai
```

### 2. Instalar los paquetes en modo editable

```powershell
pip install -e .\ragthen-core
pip install -e .\ragthen-agent
```

### 3. Crear configuracion inicial

Al primer uso, `ragthen` crea automaticamente `~/.ragthen/config.json` con valores por defecto:

```json
{
  "backend_mode": "local",
  "remote_url": "http://localhost:8000",
  "libraries_path": "C:\\Users\\<tu-usuario>\\.ragthen\\libraries",
  "vault_path": "",
  "chunk_size": 1200,
  "chunk_overlap": 250,
  "llm_model": "gpt-4o"
}
```

### 4. Configurar el agente en opencode

Copiar los archivos del agente a `~/.config/opencode/`:

```powershell
# Desde la raiz del repo
Copy-Item "ragthen-agent\.opencode\agents\ragthen.md" "$env:USERPROFILE\.config\opencode\agents\ragthen.md"
Copy-Item "ragthen-agent\.opencode\skills\analisis-multifuente\SKILL.md" "$env:USERPROFILE\.config\opencode\skills\analisis-multifuente\SKILL.md"
```

O usar el comando integrado (si `ragthen` esta en el PATH):

```powershell
ragthen setup
```

## Verificar instalacion

```powershell
# Ver CLI
ragthen --help

# Ver librerias
ragthen libraries

# Ver config
ragthen config
```

## Agregar documentos

1. Crea una carpeta en `~/.ragthen/libraries/<nombre>/`
2. Coloca PDFs, TXTs o MDs dentro
3. Indexa:

```powershell
ragthen ingest -l <nombre>
```

## Usar el agente Ragthen

El agente se invoca desde opencode:

```
/agents/ragthen "tu pregunta aqui"
```

### Comandos del agente

| Comando | Descripcion |
|---------|-------------|
| `ragthen libraries` | Listar todas las librerias y su estado de indexado |
| `ragthen search -l NAME "query" --rerank --top N` | Busqueda semantica con reranking |
| `ragthen status -l NAME` | Ver documentos indexados en una libreria |
| `ragthen config` | Ver configuracion actual |

### Comandos CLI (uso directo en terminal)

| Comando | Descripcion |
|---------|-------------|
| `ragthen ingest -l NAME` | Indexar todos los archivos de una libreria |
| `ragthen search -l NAME "query"` | Busqueda semantica (devuelve JSON) |
| `ragthen ask -l NAME "query"` | RAG completo via LLM (requiere API key de OpenAI) |
| `ragthen clear -l NAME` | Borrar el indice de una libreria |
| `ragthen vault ingest -l NAME --vault PATH` | Indexar notas de un Obsidian vault |

## Solucion de problemas

### `ragthen` no se encuentra en el terminal

Agregar al PATH:
```powershell
$env:Path += ";$env:APPDATA\Python\Python313\Scripts"
```

O reinstalar con `--no-warn-script-location` e incluir en PATH global.

### Error de importacion de modulos

Verificar que ambos paquetes esten instalados:
```powershell
pip show ragthen-core
pip show ragthen-agent
```

Si falta alguno, reinstalar en modo editable.

### ChromaDB no puede escribir en el disco

Verificar permisos en `~/.ragthen/libraries/`. El directorio `.index` dentro de cada libreria contiene la base de datos ChromaDB.

### El agente no aparece en opencode

Verificar que los archivos existen:
```powershell
ls "$env:USERPROFILE\.config\opencode\agents\ragthen.md"
ls "$env:USERPROFILE\.config\opencode\skills\analisis-multifuente\SKILL.md"
```
