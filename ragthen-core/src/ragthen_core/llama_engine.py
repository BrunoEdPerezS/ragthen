import os
import sys
import shutil
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_root / ".env")
load_dotenv(Path.home() / ".ragthen" / ".env", override=True)


from .config import load_config, get_libraries_dir

_log_tag = "[ragthen]"
INDEX_DIRNAME = ".chroma"


def _enrich_section_metadata(nodes):
    import re
    current_section = ""
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    for node in nodes:
        text = node.text or ""
        headings = heading_re.findall(text)
        if headings:
            _, title = headings[-1]
            current_section = title.strip()
        if current_section:
            if node.metadata is None:
                node.metadata = {}
            node.metadata["section"] = current_section


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
            print(f"{_log_tag} Then add PDFs/EPUBs/TXTs/MDs there and run: "
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


def _get_embedding_model():
    cfg = load_config()
    model_str = cfg.get("embedding_model", "huggingface:sentence-transformers/all-MiniLM-L6-v2")

    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    if model_str.startswith("openai:"):
        name = model_str.split(":", 1)[1]
        return OpenAIEmbedding(model=name)
    elif model_str.startswith("huggingface:"):
        name = model_str.split(":", 1)[1]
        return HuggingFaceEmbedding(model_name=name)
    else:
        return HuggingFaceEmbedding(model_name=model_str)


def _get_llm():
    cfg = load_config()
    model_name = cfg.get("llm_model", "gpt-4o")
    from llama_index.llms.openai import OpenAI
    return OpenAI(model=model_name, temperature=0.2)


def _get_chunk_size() -> tuple[int, int]:
    cfg = load_config()
    return cfg.get("chunk_size", 1024), cfg.get("chunk_overlap", 200)


def _get_reranker_config() -> dict:
    cfg = load_config()
    return cfg.get("reranker", {"type": "cross-encoder", "top_n": 10})


def _build_ingestion_pipeline(chunking_strategy: str = "sentence"):
    from llama_index.core.ingestion import IngestionPipeline
    from llama_index.core.node_parser import SentenceSplitter

    chunk_size, chunk_overlap = _get_chunk_size()

    transformations = [SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )]

    if chunking_strategy == "sentence+semantic":
        from llama_index.core.node_parser import SemanticSplitterNodeParser
        embed_model = _get_embedding_model()
        transformations.insert(0, SemanticSplitterNodeParser(
            embed_model=embed_model,
            chunk_size=chunk_size,
        ))

    transformations.append(_get_embedding_model())

    return IngestionPipeline(transformations=transformations)


def _get_local_reader():
    from llama_index.readers.file.docs.base import PDFReader
    from llama_index.readers.file import PyMuPDFReader, MarkdownReader
    from pathlib import Path as _Path

    def reader_fn(filepath: Path) -> list:
        suffix = filepath.suffix.lower()
        if suffix == ".pdf":
            reader = PDFReader()
            return reader.load_data(file=_Path(filepath))
        elif suffix == ".md":
            reader = MarkdownReader()
            return reader.load_data(file=_Path(filepath))
        else:
            from llama_index.readers.file import FlatReader
            reader = FlatReader()
            return reader.load_data(file=_Path(filepath))

    return reader_fn


def _get_llamaparse_reader(api_key: str | None = None):
    try:
        from llama_parse import LlamaParse
    except ImportError:
        return None

    return LlamaParse(
        result_type="markdown",
        api_key=api_key,
    )


def _get_vector_store(index_dir: Path):
    import chromadb
    from llama_index.vector_stores.chroma import ChromaVectorStore
    from llama_index.core import StorageContext

    index_dir.mkdir(parents=True, exist_ok=True)
    db = chromadb.PersistentClient(path=str(index_dir))
    collection = db.get_or_create_collection("ragthen")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return vector_store, storage_context, collection


def _search_to_output(nodes, query: str) -> list[dict]:
    output = []
    seen = set()
    for node in nodes:
        text = node.text or ""
        text_key = text[:100]
        if text_key in seen:
            continue
        seen.add(text_key)

        meta = node.metadata or {}
        relevance = round(float(getattr(node, 'score', 0) or 0), 4)
        relevance = max(0, min(1, relevance))

        source = (meta.get("source") or meta.get("file_name") or "unknown")
        page_label = (meta.get("page") or meta.get("page_label") or 0)

        result = {
            "source": source,
            "page": page_label,
            "relevance": relevance,
            "text": text,
        }
        if "section" in meta:
            result["section"] = meta["section"]
        output.append(result)
    return output


def ingest(library_dir: Path, index_dir: Path,
           pdfparser_mode: str = "auto",
           chunking_strategy: str = "sentence"):
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
    from llama_index.core.schema import Document

    cfg = load_config()

    files = []
    for ext in ("*.pdf", "*.epub", "*.txt", "*.md"):
        files.extend(library_dir.glob(ext))

    pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
    other_files = [f for f in files if f.suffix.lower() != ".pdf"]

    if not files:
        print(f"{_log_tag} No files found in {library_dir}")
        return

    print(f"{_log_tag} Found {len(pdf_files)} PDF(s), {len(other_files)} non-PDF(s) "
          f"in '{library_dir.name}'")

    vector_store, storage_context, collection = _get_vector_store(index_dir)
    pipeline = _build_ingestion_pipeline(chunking_strategy)
    total_chunks = 0

    def _process_pypdf(fp: Path) -> list[Document]:
        from llama_index.readers.file.docs.base import PDFReader
        from pathlib import Path as _Path
        reader = PDFReader()
        return reader.load_data(file=_Path(fp))

    def _process_llamaparse(fp: Path) -> list[Document]:
        api_key = os.environ.get("LLAMA_CLOUD_API_KEY", "")
        parser = _get_llamaparse_reader(api_key)
        if parser is None:
            print(f"{_log_tag}   LlamaParse no disponible. pip install llama-parse")
            return []
        docs = parser.load_data(str(fp))
        if isinstance(docs, list) and all(isinstance(d, Document) for d in docs):
            return docs
        result = []
        for item in docs:
            if isinstance(item, Document):
                result.append(item)
            elif hasattr(item, 'text'):
                result.append(Document(text=item.text, metadata=getattr(item, 'metadata', {})))
            elif isinstance(item, str):
                result.append(Document(text=item))
        return result

    def _count_pages(fp: Path) -> int:
        try:
            import fitz
            doc = fitz.open(fp)
            n = len(doc)
            doc.close()
            return n
        except Exception:
            return 0

    for filepath in pdf_files:
        print(f"{_log_tag}   Processing PDF: {filepath.name}")

        docs = []
        used_llamaparse = False

        if pdfparser_mode == "cloud":
            docs = _process_llamaparse(filepath)
            used_llamaparse = True
        elif pdfparser_mode == "local":
            docs = _process_pypdf(filepath)
        else:
            api_key = os.environ.get("LLAMA_CLOUD_API_KEY", "")
            if api_key:
                docs = _process_llamaparse(filepath)
                used_llamaparse = True
                if not docs or all(len((d.text or "").strip()) == 0 for d in docs):
                    print(f"{_log_tag}   LlamaParse: 0 chunks, fallback a PDFReader...")
                    docs = _process_pypdf(filepath)
            else:
                docs = _process_pypdf(filepath)

        if not docs:
            print(f"{_log_tag}   (no extractable text, skipping)")
            continue

        num_pages = _count_pages(filepath)
        if num_pages > 0 and not used_llamaparse:
            if len(docs) < max(1, num_pages // 5):
                print(f"{_log_tag}   Sugerencia: pruebe --pdfparser cloud para "
                      f"mejor calidad en '{filepath.name}'")

        for doc in docs:
            text = doc.text or ""
            if "source" not in (doc.metadata or {}):
                if doc.metadata is None:
                    doc.metadata = {}
                doc.metadata["source"] = filepath.name
            if "page" not in (doc.metadata or {}):
                if doc.metadata is None:
                    doc.metadata = {}
                doc.metadata["page"] = 0

        nodes = pipeline.run(documents=docs)
        _enrich_section_metadata(nodes)
        if not nodes:
            continue

        texts = [n.text for n in nodes if n.text]
        if not texts:
            print(f"{_log_tag}   (no text after chunking, skipping)")
            continue

        ids = [f"{filepath.stem}_{i}" for i in range(len(nodes))]
        metadatas = []
        embeddings = []
        for n in nodes:
            meta = dict(n.metadata or {})
            meta["source"] = meta.get("source") or meta.get("file_name") or filepath.name
            meta["page"] = meta.get("page") or meta.get("page_label") or 0
            # Remove non-standard keys from LlamaIndex
            meta.pop("file_name", None)
            meta.pop("page_label", None)
            metadatas.append(meta)
            emb = getattr(n, "embedding", None)
            if emb is not None:
                embeddings.append(emb)

        print(f"{_log_tag}   Indexando {len(texts)} chunks ...")

        if embeddings and len(embeddings) == len(texts):
            chroma_embeddings = embeddings
        else:
            chroma_embeddings = None

        batch_size = 200
        for i in range(0, len(texts), batch_size):
            end = min(i + batch_size, len(texts))
            kwargs = {
                "ids": ids[i:end],
                "documents": texts[i:end],
                "metadatas": metadatas[i:end],
            }
            if chroma_embeddings:
                kwargs["embeddings"] = chroma_embeddings[i:end]
            collection.add(**kwargs)

        total_chunks += len(nodes)

    for filepath in other_files:
        print(f"{_log_tag}   Processing: {filepath.name}")
        try:
            reader = SimpleDirectoryReader(input_files=[filepath])
            docs = reader.load_data()
        except Exception as e:
            print(f"{_log_tag}   Error reading {filepath.name}: {e}")
            continue

        for doc in docs:
            if doc.metadata is None:
                doc.metadata = {}
            doc.metadata.setdefault("source", filepath.name)
            doc.metadata.setdefault("page", 0)

        nodes = pipeline.run(documents=docs)
        _enrich_section_metadata(nodes)
        if not nodes:
            continue

        texts = [n.text for n in nodes if n.text]
        if not texts:
            print(f"{_log_tag}   (no text after chunking, skipping)")
            continue

        ids = [f"{filepath.stem}_{i}" for i in range(len(nodes))]

        metadatas = []
        embeddings = []
        for n in nodes:
            meta = dict(n.metadata or {})
            meta["source"] = meta.get("source") or meta.get("file_name") or filepath.name
            meta["page"] = meta.get("page") or meta.get("page_label") or 0
            meta.pop("file_name", None)
            meta.pop("page_label", None)
            metadatas.append(meta)
            emb = getattr(n, "embedding", None)
            if emb is not None:
                embeddings.append(emb)

        print(f"{_log_tag}   Indexando {len(texts)} chunks ...")

        if embeddings and len(embeddings) == len(texts):
            chroma_embeddings = embeddings
        else:
            chroma_embeddings = None

        batch_size = 200
        for i in range(0, len(texts), batch_size):
            end = min(i + batch_size, len(texts))
            kwargs = {
                "ids": ids[i:end],
                "documents": texts[i:end],
                "metadatas": metadatas[i:end],
            }
            if chroma_embeddings:
                kwargs["embeddings"] = chroma_embeddings[i:end]
            collection.add(**kwargs)

        total_chunks += len(nodes)

    print(f"{_log_tag} Ingestion complete — {total_chunks} chunks indexed "
          f"in '{library_dir.name}'")


def search(query: str, index_dir: Path, top_k: int = 5,
           relevance_threshold: float = 0.0, rerank: bool = False,
           reranker_type: str = "cross-encoder") -> list[dict]:
    from llama_index.core import VectorStoreIndex, Settings

    if not index_dir.exists():
        return []

    embed_model = _get_embedding_model()
    Settings.embed_model = embed_model

    vector_store, storage_context, collection = _get_vector_store(index_dir)

    try:
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context,
            embed_model=embed_model,
        )
    except Exception:
        return []

    retrieve_k = max(top_k * 3, 15) if rerank else top_k
    retriever = index.as_retriever(similarity_top_k=retrieve_k)

    nodes = retriever.retrieve(query)
    if not nodes:
        return []

    if rerank:
        rr_config = _get_reranker_config()
        rr_type = reranker_type or rr_config.get("type", "cross-encoder")
        rr_top_n = rr_config.get("top_n", min(top_k, 10))

        if rr_type == "llm":
            try:
                from llama_index.core.postprocessor import LLMRerank
                llm = _get_llm()
                postprocessor = LLMRerank(
                    llm=llm,
                    choice_batch_size=5,
                    top_n=rr_top_n,
                )
                nodes = postprocessor.postprocess_nodes(nodes, query_str=query)
            except Exception:
                pass
        elif rr_type == "reorder":
            try:
                from llama_index.core.postprocessor import LongContextReorder
                postprocessor = LongContextReorder()
                nodes = postprocessor.postprocess_nodes(nodes)
            except Exception:
                pass
        else:
            try:
                from llama_index.core.postprocessor import SentenceTransformerRerank
                postprocessor = SentenceTransformerRerank(
                    model="cross-encoder/ms-marco-MiniLM-L-6-v2",
                    top_n=rr_top_n,
                )
                nodes = postprocessor.postprocess_nodes(nodes, query_str=query)
            except Exception:
                pass

    output = _search_to_output(nodes[:top_k], query)
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
    if not index_dir.exists():
        print(f"{_log_tag} No index found in '{lib_name}'. "
              f"Run: ragthen ingest -l {lib_name}")
        return

    from llama_index.core import VectorStoreIndex

    vector_store, storage_context, collection = _get_vector_store(index_dir)

    try:
        count = collection.count()
    except Exception:
        count = 0

    print(f"{_log_tag} Library '{lib_name}' — {count} indexed chunks")

    if count > 0:
        sources = set()
        BATCH = 2000
        for offset in range(0, count, BATCH):
            batch = collection.get(limit=min(BATCH, count - offset), offset=offset,
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
            from llama_index.core import VectorStoreIndex
            _, _, collection = _get_vector_store(index_dir)
            try:
                count = collection.count()
            except Exception:
                count = 0
            print(f"    {name:30s} {count} chunks indexed")
        else:
            print(f"    {name:30s} (not indexed)")
