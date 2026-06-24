import re
import sys
from pathlib import Path

_embedding_model = None
_log_tag = "[ragthen]"

INDEX_DIRNAME = ".index"

_HEADING_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def get_collection(index_dir: Path):
    import chromadb
    client = chromadb.PersistentClient(path=str(index_dir))
    return client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})


def extract_pdf_pages(filepath: Path) -> list[dict]:
    import fitz
    doc = fitz.open(str(filepath))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append({"text": text, "page": i + 1, "source": filepath.name})
    doc.close()
    return pages


def extract_text_file(filepath: Path) -> list[dict]:
    text = filepath.read_text(encoding="utf-8", errors="replace")
    return [{"text": text, "page": 1, "source": filepath.name}]


def _mathml_to_latex(element) -> str:
    tag = getattr(element, "name", None)
    if tag is None:
        return ""

    children = [c for c in element.children if hasattr(c, "name")]

    if tag == "math":
        parts = [_mathml_to_latex(c) for c in children]
        return "".join(parts)

    if tag == "mrow":
        parts = [_mathml_to_latex(c) for c in children]
        return " ".join(parts)

    if tag == "mi":
        text = element.get_text() or ""
        return text.strip()

    if tag == "mn":
        text = element.get_text() or ""
        return text.strip()

    if tag == "mo":
        text = element.get_text() or ""
        text = text.strip()
        if text in ("=", "+", "-", "/", "*", "<", ">", "(", ")", "[", "]", "{", "}"):
            return " " + text + " "
        return " " + text + " "

    if tag == "msup":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        exp = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return base + "^{" + exp + "}"

    if tag == "msub":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        sub = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return base + "_{" + sub + "}"

    if tag == "msubsup":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        sub = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        sup = _mathml_to_latex(children[2]) if len(children) > 2 else ""
        return base + "_{" + sub + "}^{" + sup + "}"

    if tag == "mfrac":
        num = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        den = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return "\\frac{" + num + "}{" + den + "}"

    if tag == "msqrt":
        inner = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        return "\\sqrt{" + inner + "}"

    if tag == "mroot":
        inner = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        root = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return "\\sqrt[" + root + "]{" + inner + "}"

    if tag == "munder":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        under = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return base + "_{" + under + "}"

    if tag == "mover":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        over = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        return "\\bar{" + base + "}^{" + over + "}"

    if tag == "munderover":
        base = _mathml_to_latex(children[0]) if len(children) > 0 else ""
        under = _mathml_to_latex(children[1]) if len(children) > 1 else ""
        over = _mathml_to_latex(children[2]) if len(children) > 2 else ""
        return "\\sum_{" + under + "}^{" + over + "} " + base

    if tag == "mtext":
        text = element.get_text() or ""
        return "\\text{" + text.strip() + "}"

    parts = []
    if hasattr(element, "string") and element.string:
        parts.append(str(element.string))
    for child in children:
        parts.append(_mathml_to_latex(child))
    return " ".join(parts)


def _xhtml_to_markdown(xhtml_body: str) -> str:
    from markdownify import MarkdownConverter

    class MathConverter(MarkdownConverter):
        def convert_math(self, el, text, parent_tags=None):
            alttext = el.get("alttext", "")
            display = el.get("display", "")
            is_block = (display == "block" or el.get("display", "") == "block")
            try:
                latex = _mathml_to_latex(el)
            except Exception:
                if alttext:
                    latex = alttext
                else:
                    return "[equation]"

            if is_block:
                return "\n\n$$" + latex.strip() + "$$\n\n"
            return "$" + latex.strip() + "$"

    return MathConverter(heading_style="ATX").convert(xhtml_body)


def _extract_epub_title_from_xhtml(xhtml_content: str) -> str:
    import re
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xhtml_content, re.DOTALL | re.IGNORECASE)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def extract_epub_pages(filepath: Path) -> list[dict]:
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        print(f"{_log_tag} epub support requires ebooklib: pip install ebooklib")
        return []

    try:
        book = epub.read_epub(str(filepath), {"ignore_ncx": True})
    except Exception as e:
        if "drm" in str(e).lower() or "encrypt" in str(e).lower():
            print(f"{_log_tag} Cannot read DRM-protected EPUB: {filepath.name}")
        else:
            print(f"{_log_tag} Cannot open EPUB (malformed or corrupt): {filepath.name}", file=sys.stderr)
        return []

    pages = []
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    spine = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

    all_items = list(book.get_items())

    for idx, item in enumerate(spine):
        try:
            xhtml = item.get_content().decode("utf-8", errors="replace")
        except Exception:
            continue

        if not xhtml.strip():
            continue

        chapter_title = _extract_epub_title_from_xhtml(xhtml)
        if not chapter_title:
            for ai in all_items:
                if ai.get_id() == item.get_id() or ai.get_name() == item.get_name():
                    chapter_title = getattr(ai, "title", "") or ""
                    break

        md_text = _xhtml_to_markdown(xhtml)

        if not md_text.strip():
            continue

        pages.append({
            "text": md_text,
            "page": idx + 1,
            "source": filepath.name,
            "chapter_title": chapter_title,
        })

    return pages


def chunk_pages(pages: list[dict], chunk_size: int = 1200,
                chunk_overlap: int = 250,
                heading_aware: bool = False) -> list[dict]:
    chunks = []
    if not heading_aware:
        stride = max(chunk_size - chunk_overlap, 1)
        for page in pages:
            text = page["text"]
            source = page["source"]
            page_num = page["page"]
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({"text": chunk_text, "source": source, "page": page_num})
                if end == len(text):
                    break
                start += stride
        return chunks

    fenced_re = re.compile(r"^(```|~~~)", re.MULTILINE)
    heading_line_re = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)

    for page in pages:
        text = page["text"]
        source = page["source"]
        page_num = page["page"]

        lines = text.split("\n")
        section_breaks = []
        in_code_block = False
        fence_char = ""
        char_offset = 0

        for line_idx, line in enumerate(lines):
            fence_match = fenced_re.match(line)
            if fence_match:
                if not in_code_block:
                    in_code_block = True
                    fence_char = fence_match.group(1)
                elif fence_match.group(1) == fence_char:
                    in_code_block = False
                char_offset += len(line) + 1
                continue

            if in_code_block:
                char_offset += len(line) + 1
                continue

            heading_match = heading_line_re.match(line)
            if heading_match:
                header_start = char_offset
                section_breaks.append({
                    "pos": header_start,
                    "level": len(heading_match.group(1)),
                    "title": heading_match.group(2).strip(),
                })

            char_offset += len(line) + 1

        if not section_breaks:
            stride = max(chunk_size - chunk_overlap, 1)
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append({"text": chunk_text, "source": source, "page": page_num})
                if end == len(text):
                    break
                start += stride
            continue

        section_breaks.insert(0, {"pos": 0, "level": 0, "title": ""})

        section_hierarchy = []

        for i in range(len(section_breaks)):
            sb = section_breaks[i]
            start_pos = sb["pos"]
            end_pos = section_breaks[i + 1]["pos"] if i + 1 < len(section_breaks) else len(text)

            while section_hierarchy and section_hierarchy[-1][0] >= sb["level"]:
                section_hierarchy.pop()
            if sb["title"]:
                section_hierarchy.append((sb["level"], sb["title"]))

            section_path = " > ".join(t for _, t in section_hierarchy)

            section_text = text[start_pos:end_pos].strip()
            if not section_text:
                continue

            if len(section_text) <= chunk_size:
                chunk_meta = {"text": section_text, "source": source, "page": page_num}
                if section_path:
                    chunk_meta["section"] = section_path
                chunks.append(chunk_meta)
            else:
                stride = max(chunk_size - chunk_overlap, 1)
                sub_start = 0
                while sub_start < len(section_text):
                    end = min(sub_start + chunk_size, len(section_text))
                    chunk_text = section_text[sub_start:end].strip()
                    if chunk_text:
                        chunk_meta = {"text": chunk_text, "source": source, "page": page_num}
                        if section_path:
                            chunk_meta["section"] = section_path
                        chunks.append(chunk_meta)
                    if end == len(section_text):
                        break
                    sub_start += stride

    return chunks
