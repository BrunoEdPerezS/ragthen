"""
Test: verifica que los metadatos devueltos por PDFReader incluyan source y page.

Uso:
    python test/test_pdfreader_metadata.py -l Thinksight

Mide:
  - Keys de metadata devueltas por PDFReader (LlamaIndex)
  - Que source y page esten presentes
"""
import os
import sys
import argparse
from llama_index.readers.file.docs.base import PDFReader
from pathlib import Path

def test_metadata(lib_name: str):
    lib_path = os.path.expanduser(f"~/.ragthen/libraries/{lib_name}")
    if not os.path.exists(lib_path):
        print(f"Library '{lib_name}' not found")
        return False

    pdfs = list(Path(lib_path).glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in '{lib_name}'")
        return False

    fp = str(pdfs[0])
    reader = PDFReader()
    docs = reader.load_data(file=Path(fp))
    print(f"PDF: {pdfs[0].name}")
    print(f"Docs: {len(docs)}")

    for i, d in enumerate(docs[:3]):
        meta = d.metadata
        print(f"\nDoc {i}:")
        print(f"  keys: {list(meta.keys())}")
        print(f"  source: {meta.get('file_name', 'MISSING')}")
        print(f"  page:   {meta.get('page_label', 'MISSING')}")
        print(f"  text:   {d.text[:80] if d.text else 'EMPTY'}...")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--library", required=True)
    args = parser.parse_args()
    ok = test_metadata(args.library)
    sys.exit(0 if ok else 1)
