"""
Test: compara extractores PDF (PyMuPDF vs pdfplumber vs PDFReader de LlamaIndex).

Uso:
    python test/test_pdf_extractors.py

Mide:
  - Chars extraidos por pagina
  - Paginas vacias (donde un extractor encuentra texto y otro no)
  - Tamano de muestra del texto extraido
"""
import os

LIBRARIES = os.path.expanduser("~/.ragthen/libraries")

TARGETS = [
    {
        "name": "Kotler (encoding)",
        "path": os.path.join(LIBRARIES, "Retsell", "Fundamentos del Marketing-Kotler.pdf"),
        "pages": [2, 3],
    },
    {
        "name": "Anderson (baseline)",
        "path": os.path.join(LIBRARIES, "Thinksight", "Anderson,Johnson - Systems Thinking Basics.pdf"),
        "pages": [3, 4],
    },
]

def extract_pymupdf(filepath, page_num):
    import fitz
    doc = fitz.open(filepath)
    page = doc[page_num - 1]
    text = page.get_text()
    doc.close()
    return text

def extract_pypdf(filepath, page_num):
    from llama_index.readers.file.docs.base import PDFReader
    from pathlib import Path
    reader = PDFReader()
    docs = reader.load_data(file=Path(filepath))
    if page_num - 1 < len(docs):
        return docs[page_num - 1].text or ""
    return ""

def extract_pdfplumber(filepath, page_num):
    import pdfplumber
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[page_num - 1]
        return page.extract_text() or ""

if __name__ == "__main__":
    for target in TARGETS:
        fp = target["path"]
        if not os.path.exists(fp):
            print(f"[SKIP] {target['name']}")
            continue

        print(f"\n{'>'*60}")
        print(f"PDF: {target['name']}")
        print(f"{'>'*60}")

        for pg in target["pages"]:
            print(f"\n--- Pagina {pg} ---")
            t1 = extract_pymupdf(fp, pg)
            t2 = extract_pypdf(fp, pg)
            t3 = extract_pdfplumber(fp, pg)

            print(f"  PyMuPDF:    {len(t1):6} chars, vacio={len(t1.strip())==0}")
            print(f"  PDFReader:  {len(t2):6} chars, vacio={len(t2.strip())==0}")
            print(f"  pdfplumber: {len(t3):6} chars, vacio={len(t3.strip())==0}")

            winner = max([(len(t1), "PyMuPDF"), (len(t2), "PDFReader"), (len(t3), "pdfplumber")])
            print(f"  Ganador: {winner[1]} ({winner[0]} chars)")

            print(f"  Sample PDFReader: |{t2[:200]}|")
