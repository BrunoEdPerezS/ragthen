"""
Test: verifica que ChromaDB tenga embeddings almacenados correctamente.

Uso:
    python test/test_chroma_embeddings.py -l Thinksight

Mide:
  - Cantidad de chunks indexados
  - Dimension de embeddings
  - Query de prueba (busca el chunk mas cercano a si mismo, debe dar distancia 0)
"""
import os
import sys
import argparse
import chromadb

def test_library(lib_name: str):
    lib_path = os.path.expanduser(f"~/.ragthen/libraries/{lib_name}/.chroma")
    if not os.path.exists(lib_path):
        print(f"Library '{lib_name}' not found or not indexed")
        return False

    db = chromadb.PersistentClient(path=lib_path)
    col = db.get_collection("ragthen")
    count = col.count()
    print(f"Library: {lib_name}")
    print(f"Chunks:  {count}")

    data = col.get(limit=3, include=["embeddings", "documents", "metadatas"])
    if not data["embeddings"] or len(data["embeddings"]) == 0:
        print("ERROR: No embeddings found in ChromaDB")
        return False

    emb = data["embeddings"][0]
    print(f"Embedding dim: {len(emb)}")
    print(f"Sample values: {emb[:3]}")
    print(f"First doc:     {data['documents'][0][:80]}...")
    print(f"Source:        {data['metadatas'][0].get('source', 'N/A')}")
    print(f"Page:          {data['metadatas'][0].get('page', 'N/A')}")

    qr = col.query(query_embeddings=[emb], n_results=3)
    print(f"\nQuery test: {len(qr['ids'][0])} results")
    for i, (doc_id, dist) in enumerate(zip(qr['ids'][0], qr['distances'][0])):
        print(f"  {i}: {doc_id}  dist={dist:.4f}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--library", required=True)
    args = parser.parse_args()
    ok = test_library(args.library)
    sys.exit(0 if ok else 1)
