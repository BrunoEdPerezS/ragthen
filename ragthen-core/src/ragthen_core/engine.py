import os
import sys
import shutil
from pathlib import Path

from .config import load_config, get_libraries_dir
from .storage import (_get_embedding_model, get_collection, extract_pdf_pages,
                       extract_text_file, chunk_pages, INDEX_DIRNAME)
from .rerank import rerank as _rerank_fn

_log_tag = "[ragthen]"


def _list_libraries() -> list[str]:
    lib_dir = get_libraries_dir()
    if not lib_dir.exists():
        return []
    return sorted(
        d.name
        for d in lib_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")
    )


def _auto_detect() -> str | None:
    names = _list_libraries()
    if len(names) == 1:
        return names[0]
    return None


def resolve_library(name: str | None = None) -> tuple[Path, Path]:
    if name is None:
        name = _auto_detect()
    if name is None:
        names = _list_libraries()
        if not names:
            print(f"{_log_tag} No libraries found in {get_libraries_dir()}/")
            print(f"{_log_tag} Create one: New-Item -ItemType Directory -Path "
                  f"'{get_libraries_dir()}/mylib'")
            print(f"{_log_tag} Then add PDFs/TXTs/MDs there and run: "
                  f"ragthen ingest -l mylib")
            sys.exit(1)
        print(f"{_log_tag} Multiple libraries found. Use -l NAME to pick one.")
        for n in names:
            print(f"        -l {n}")
        sys.exit(1)

    lib_dir = get_libraries_dir() / name
    if not lib_dir.is_dir():
        print(f"{_log_tag} Library '{name}' not found at {lib_dir}")
        print(f"{_log_tag} Create it first: New-Item -ItemType Directory -Path '{lib_dir}'")
        sys.exit(1)

    index_dir = lib_dir / INDEX_DIRNAME
    return lib_dir, index_dir


def ingest(library_dir: Path, index_dir: Path):
    cfg = load_config()
    chunk_size = cfg.get("chunk_size", 1200)
    chunk_overlap = cfg.get("chunk_overlap", 250)

    pdf_files = list(library_dir.glob("*.pdf"))
    txt_files = list(library_dir.glob("*.txt"))
    md_files = list(library_dir.glob("*.md"))

    if not pdf_files and not txt_files and not md_files:
        print(f"{_log_tag} No files found in {library_dir}")
        print(f"{_log_tag} Place PDF, TXT, or MD files there and re-run.")
        return

    print(f"{_log_tag} Found {len(pdf_files)} PDF(s), {len(txt_files)} text file(s), "
          f"{len(md_files)} MD file(s) in '{library_dir.name}'")
    print(f"{_log_tag} Loading embedding model (all-MiniLM-L6-v2, ~80MB)...")

    model = _get_embedding_model()
    collection = get_collection(index_dir)
    total_chunks = 0

    for filepath in pdf_files + txt_files + md_files:
        print(f"{_log_tag}   Processing: {filepath.name}")

        if filepath.suffix.lower() == ".pdf":
            pages = extract_pdf_pages(filepath)
        else:
            pages = extract_text_file(filepath)

        chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            print(f"{_log_tag}   (no extractable text, skipping)")
            continue

        texts = [c["text"] for c in chunks]
        ids = [f"{filepath.stem}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": c["source"], "page": c["page"]} for c in chunks]

        print(f"{_log_tag}   Embedding {len(texts)} chunks ...")
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        batch_size = 200
        for i in range(0, len(texts), batch_size):
            end = i + batch_size
            collection.add(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=texts[i:end],
                metadatas=metadatas[i:end],
            )

        total_chunks += len(chunks)

    print(f"{_log_tag} Ingestion complete — {total_chunks} chunks indexed "
          f"in '{library_dir.name}'")


def search(query: str, index_dir: Path, top_k: int = 5,
           relevance_threshold: float = 0.0, rerank: bool = False) -> list[dict]:
    model = _get_embedding_model()
    collection = get_collection(index_dir)

    retrieve_k = max(top_k * 3, 15) if rerank else top_k

    q_emb = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=q_emb, n_results=retrieve_k,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(results["documents"][0],
                                results["metadatas"][0],
                                results["distances"][0]):
        relevance = round(max(0, 1 - dist / 2), 4)
        if relevance < relevance_threshold:
            continue
        output.append({
            "source": meta["source"],
            "page": meta["page"],
            "relevance": relevance,
            "text": doc,
        })

    if rerank and output:
        output = _rerank_fn(query, output, top_k)
        if relevance_threshold > 0:
            output = [p for p in output if p["relevance"] >= relevance_threshold]

    return output


_PROMPT_TEMPLATE = (
    "You are a precise research assistant with access to the user's personal library. "
    "Answer ONLY using the context provided below. If the context does not contain "
    "enough information to answer, say so clearly. ALWAYS cite your sources in brackets: "
    "[Source: filename, Page X].\n\n"
    "=== CONTEXT FROM LIBRARY ===\n"
    "{context}\n"
    "=== END OF CONTEXT ===\n\n"
    "Question: {question}\n\n"
    "Answer (concise, with citations):"
)


def ask(query: str, index_dir: Path, lib_name: str,
        api_key: str | None = None, model_name: str = "gpt-4o") -> str:
    passages = search(query, index_dir, top_k=6)

    if not passages:
        return f"{_log_tag} No relevant passages found in '{lib_name}'."

    context_parts = []
    for p in passages:
        context_parts.append(f"[Source: {p['source']}, Page {p['page']}]\n{p['text']}")
    context = "\n\n---\n\n".join(context_parts)

    prompt = _PROMPT_TEMPLATE.format(context=context, question=query)

    if api_key:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    else:
        return (
            f"{_log_tag} No API key provided — returning raw context only.\n\n"
            "=== RAW CONTEXT (use this to answer) ===\n\n"
            + context
        )


def status(index_dir: Path, lib_name: str):
    if not index_dir.exists() or not list(index_dir.iterdir()):
        print(f"{_log_tag} No index found in '{lib_name}'. "
              f"Run: ragthen ingest -l {lib_name}")
        return

    col = get_collection(index_dir)
    count = col.count()
    print(f"{_log_tag} Library '{lib_name}' — {count} indexed chunks")

    if count > 0:
        sources = set()
        BATCH = 2000
        for offset in range(0, count, BATCH):
            batch = col.get(limit=min(BATCH, count - offset), offset=offset,
                            include=["metadatas"])
            for m in batch["metadatas"]:
                if "source" in m:
                    sources.add(m["source"])
        sources = sorted(sources)
        print(f"{_log_tag}   Documents ({len(sources)}):")
        for s in sources:
            print(f"      - {s}")


def clear(index_dir: Path, lib_name: str):
    if index_dir.exists():
        shutil.rmtree(index_dir)
        print(f"{_log_tag} Index cleared for '{lib_name}'.")
    else:
        print(f"{_log_tag} Nothing to clear in '{lib_name}'.")


def list_libraries():
    names = _list_libraries()
    lib_dir = get_libraries_dir()
    if not names:
        print(f"{_log_tag} No libraries found in {lib_dir}/")
        print(f"{_log_tag} Create one: New-Item -ItemType Directory -Path '{lib_dir}/mylib'")
        return

    print(f"{_log_tag} Available libraries ({len(names)}):")
    for name in names:
        index_dir = lib_dir / name / INDEX_DIRNAME
        if index_dir.exists():
            col = get_collection(index_dir)
            count = col.count()
            print(f"    {name:30s} {count} chunks indexed")
        else:
            print(f"    {name:30s} (not indexed)")
