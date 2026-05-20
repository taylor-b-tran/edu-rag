import os, time
import chromadb
from chromadb.config import Settings
from src.document_processor.seed_documents import SEED_DOCUMENTS

# ── ChromaDB connection ──
CHROMA_HOST = os.getenv("CHROMA_HOST", "")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
 
# ── Collection / course config ──
COLLECTION  = "csit321_course"
COURSE_ID   = "CSIT321"
 
# ── Threshold ──
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))   
DISTANCE_THRESHOLD   = float(os.getenv("DISTANCE_THRESHOLD",   "0.65")) 

def _load_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        try:
            dim = model.get_embedding_dimension()
        except AttributeError:
            dim = model.get_sentence_embedding_dimension()
        print(f"  [INFO] Using SentenceTransformer all-MiniLM-L6-v2 (dim={dim})")
        return model, "all-MiniLM-L6-v2", dim
    except Exception as exc:
        print(
            f"WARNING: SentenceTransformer unavailable ({type(exc).__name__}) \n"
            f" Falling back to OfflineEmbedder (FNV-1a hash, dim=384). \n"
            f" Retrieval quality will be significantly lower. \n"
            f" Install sentence-transformers to restore full quality. \n"
        )
        from src.document_processor.offline_embedder import OfflineEmbedder
        model = OfflineEmbedder()
        return model, model.MODEL_NAME, model.get_sentence_embedding_dimension()

def get_chroma_client() -> chromadb.ClientAPI:
    if CHROMA_HOST:
        print(f"[INFO] Connecting to ChromaDB HTTP service at {CHROMA_HOST}:{CHROMA_PORT}")
        return chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False),
        )
    print(f"[INFO] Using local ChromaDB PersistentClient at {CHROMA_PATH}")
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_or_create_collection(client: chromadb.ClientAPI):
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

def ingest(force_reload: bool = False) -> dict:
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
    print(f"  ChromaDB target : {CHROMA_HOST + ':' + str(CHROMA_PORT) if CHROMA_HOST else CHROMA_PATH}")
    print(f"  Collection      : {COLLECTION}")
    print(f"  Course ID       : {COURSE_ID}")
    print(f"  Seed documents  : {len(SEED_DOCUMENTS)}")
    print(f"  Existing chunks : {collection.count()}")
    print(f"  Sim threshold   : {SIMILARITY_THRESHOLD}  (distance equiv: {DISTANCE_THRESHOLD})")
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
        collection.upsert(
            ids=ids, documents=texts,
            embeddings=embeddings, metadatas=metadatas,
        )

    elapsed = time.time() - t0
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
        include=["documents", "distances", "metadatas"],
    )

    if result["documents"][0]:
        dist = result["distances"][0][0]
        meta = result["metadatas"][0][0]
        sim  = max(0.0, 1.0 - dist)
        print(f"  [TEST] Best match : {meta['source_file']} p.{meta['page_number']}")
        print(f"  [TEST] Similarity : {sim:.4f}  Distance: {dist:.4f}  Topic: {meta['topic']}")
        status = "PASSED" if sim >= SIMILARITY_THRESHOLD else "WARN – below threshold"
        print(f"  [TEST] {status}")
    else:
        print("  [WARN] No results returned.")

    summary = {
        "total_documents": len(SEED_DOCUMENTS),
        "upserted": len(ids),
        "errors": errors,
        "collection_count": final_count,
        "embed_model": model_name,
        "embed_dim": dim,
        "elapsed_s": round(elapsed, 2),
        "chroma_target": f"http://{CHROMA_HOST}:{CHROMA_PORT}" if CHROMA_HOST else CHROMA_PATH,
        "status": "ok" if not errors else "partial",
    }
    print(f"\n{'='*62}")
    print(f"  Status: {summary['status'].upper()}")
    print(f"{'='*62}\n")
    return summary

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Delete and re-create the collection")
    args = p.parse_args()
    ingest(force_reload=args.force)
