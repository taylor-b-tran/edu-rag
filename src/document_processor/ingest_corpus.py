import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import chromadb
from document_processor.seed_documents import SEED_DOCUMENTS

CHROMA_PATH          = os.getenv("CHROMA_PATH", "./chroma_data")
COLLECTION           = "csit321_course"
COURSE_ID            = "CSIT321"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))

def _load_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        dim   = model.get_sentence_embedding_dimension()
        print(f"  [INFO] Using SentenceTransformer (dim={dim})")
        return model, "all-MiniLM-L6-v2", dim
    except Exception as exc:
        print(f"  [WARN] SentenceTransformer unavailable; using offline embedder.")
        from modules.offline_embedder import OfflineEmbedder
        model = OfflineEmbedder()
        return model, model.MODEL_NAME, model.get_sentence_embedding_dimension()

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_or_create_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"})

def ingest(force_reload=False):
    print(f"\n{'='*62}")
    print("  EduRAG – Seeded Corpus Ingestion  (S5-T17)")
    print(f"{'='*62}")

    client = get_chroma_client()
    if force_reload:
        try:
            client.delete_collection(COLLECTION)
            print("  [INFO] Deleted existing collection.")
        except Exception:
            pass

    collection = get_or_create_collection(client)
    print(f"  ChromaDB path   : {CHROMA_PATH}")
    print(f"  Collection      : {COLLECTION}")
    print(f"  Course ID       : {COURSE_ID}")
    print(f"  Seed documents  : {len(SEED_DOCUMENTS)}")
    print(f"  Existing chunks : {collection.count()}")
    print()

    model, model_name, dim = _load_embedder()
    print(f"  Embedding model : {model_name}  dim={dim}\n")

    ids, texts, embeddings, metadatas, errors = [], [], [], [], []
    t0 = time.time()

    for doc in SEED_DOCUMENTS:
        try:
            emb = model.encode(doc["text"], normalize_embeddings=True)
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            ids.append(doc["doc_id"])
            texts.append(doc["text"])
            embeddings.append(emb)
            metadatas.append({
                "course_id"  : COURSE_ID,
                "source_file": doc["source_file"],
                "page_number": doc["page_number"],
                "topic"      : doc["topic"],
                "week"       : doc["week"],
            })
            print(f"  [OK] {doc['doc_id']}")
        except Exception as exc:
            errors.append({"doc_id": doc["doc_id"], "error": str(exc)})
            print(f"  [ERR] {doc['doc_id']}: {exc}")

    if ids:
        collection.upsert(ids=ids, documents=texts,
                          embeddings=embeddings, metadatas=metadatas)

    elapsed     = time.time() - t0
    final_count = collection.count()
    print(f"\n  [OK] Upserted {len(ids)} chunks  ({elapsed:.1f}s)")
    print(f"  [OK] Collection total: {final_count} chunks")

    # Smoke-test
    print("\n  [TEST] Smoke-test: 'What is RAG?' ...")
    q_emb = model.encode("What is RAG?", normalize_embeddings=True)
    if hasattr(q_emb, "tolist"):
        q_emb = q_emb.tolist()
    result = collection.query(
        query_embeddings=[q_emb], n_results=1,
        where={"course_id": {"$eq": COURSE_ID}},
        include=["documents", "distances", "metadatas"])
    if result["documents"][0]:
        dist = result["distances"][0][0]
        meta = result["metadatas"][0][0]
        sim  = max(0.0, 1.0 - dist)
        print(f"  [TEST] Best match : {meta['source_file']} p.{meta['page_number']}")
        print(f"  [TEST] Similarity : {sim:.4f}   Topic: {meta['topic']}")
        print("  [TEST] PASSED ✓")
    else:
        print("  [WARN] No results returned.")

    summary = {
        "total_documents": len(SEED_DOCUMENTS), "upserted": len(ids),
        "errors": errors, "collection_count": final_count,
        "embed_model": model_name, "embed_dim": dim,
        "elapsed_s": round(elapsed, 2),
        "status": "ok" if not errors else "partial",
    }
    print(f"\n{'='*62}")
    print(f"  Status: {summary['status'].upper()}")
    print(f"{'='*62}\n")
    return summary

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    ingest(force_reload=args.force)
