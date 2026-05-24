import os, requests
from dataclasses import dataclass, field
from typing import List, Optional
from src.document_processor.ingest_corpus import (
    get_chroma_client, get_or_create_collection,
    CHROMA_PATH, COLLECTION, COURSE_ID, SIMILARITY_THRESHOLD, _load_embedder
)

TOP_K        = int(os.getenv("TOP_K", "5"))
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
FALLBACK_LABEL = "Based on general knowledge \u2014 not verified against course materials."

@dataclass
class RetrievedChunk:
    chunk_id: str; text: str; source_file: str
    page_number: int; topic: str; week: str; distance: float

    @property
    def similarity(self):
        return max(0.0, 1.0 - self.distance)

    def citation_label(self):
        return f"{self.source_file} (p.{self.page_number})"

@dataclass
class GeneratedResponse:
    answer: str; source_refs: List[dict]; is_fallback: bool
    model_used: str; top_chunks: List[RetrievedChunk]
    confidence: str; confidence_score: float

class VectorRetriever:
    def __init__(self):
        client           = get_chroma_client()
        self._collection = get_or_create_collection(client)
        self._model, self._model_name, _ = _load_embedder()
        print(f"  [Retriever] '{COLLECTION}' has {self._collection.count()} chunks  "
              f"(model: {self._model_name})")

    def search(self, query: str, course_id=COURSE_ID, top_k=TOP_K) -> List[RetrievedChunk]:
        q_emb = self._model.encode(query, normalize_embeddings=True)
        if hasattr(q_emb, "tolist"):
            q_emb = q_emb.tolist()
        res = self._collection.query(
            query_embeddings=[q_emb], n_results=top_k,
            where={"course_id": {"$eq": course_id}},
            include=["documents", "distances", "metadatas"])
        chunks = []
        for i, cid in enumerate(res["ids"][0]):
            meta = res["metadatas"][0][i]
            chunks.append(RetrievedChunk(
                chunk_id=cid, text=res["documents"][0][i],
                source_file=meta.get("source_file","Unknown"),
                page_number=int(meta.get("page_number",0)),
                topic=meta.get("topic",""), week=meta.get("week",""),
                distance=res["distances"][0][i]))
        return chunks

class LLMResponseGeneration:
    def __init__(self, retriever=None):
        self._retriever = retriever or VectorRetriever()

    def _build_prompt(self, query, chunks, history=None):
        sys_instr = (
            "You are Paedia, a course assistant for CSIT321 at UOW.\n"
            "Answer ONLY from the CONTEXT sections below.\n"
            "Always cite the source file and page number.\n"
            "If context is insufficient, say so clearly.\n\n"
        )
        if not chunks:
            ctx = f"[NO COURSE MATERIAL FOUND]\n{FALLBACK_LABEL}\n"
        else:
            parts = []
            for i, ch in enumerate(chunks, 1):
                parts.append(
                    f"--- CONTEXT {i} | {ch.source_file} p.{ch.page_number} "
                    f"[{ch.topic}] sim={ch.similarity:.2f} ---\n{ch.text}\n")
            ctx = "\n".join(parts)

        hist = ""
        if history:
            lines = []
            for t in history[-3:]:
                lines += [f"Student: {t.get('question','')}", f"Paedia: {t.get('answer','')}"]
            hist = "\n[HISTORY]\n" + "\n".join(lines) + "\n"

        return (f"{sys_instr}{hist}\n[COURSE MATERIAL]\n{ctx}\n\n"
                f"[STUDENT QUESTION]\n{query}\n\n[PAEDIA ANSWER]")

    def _call_ollama(self, prompt, chunks=None):
        chunks = chunks or []
        try:
            resp = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.1, "num_predict": 512}},
                timeout=120)
            resp.raise_for_status()
            return resp.json().get("response","").strip(), True
        except requests.exceptions.ConnectionError:
            context_lines = (
                "\n".join(f"\u2022 {c.citation_label()}: {c.text[:200]}\u2026" for c in chunks)
                if chunks else "  (no chunks retrieved)"
            )
            return (
                "[Ollama not running] Start with: ollama serve && ollama pull llama3.2\n\n"
                "Retrieved context (retrieval succeeded):\n" + context_lines
            ), False
        except Exception as exc:
            return f"[LLM Error: {exc}]", False

    @staticmethod
    def _confidence(chunks):
        if not chunks: return "Low", 0.0
        avg = sum(c.similarity for c in chunks) / len(chunks)
        label = "High" if avg >= 0.60 else ("Medium" if avg >= 0.35 else "Low")
        return label, round(avg, 3)

    @staticmethod
    def _source_refs(chunks):
        seen, refs = set(), []
        for ch in chunks:
            k = (ch.source_file, ch.page_number)
            if k not in seen:
                seen.add(k)
                refs.append({"source_file": ch.source_file, "page": ch.page_number,
                             "topic": ch.topic, "week": ch.week,
                             "similarity": round(ch.similarity, 3)})
        return refs

    def generate(self, query, course_id=COURSE_ID, top_k=TOP_K,
                 history=None) -> "GeneratedResponse":
        all_chunks  = self._retriever.search(query, course_id=course_id, top_k=top_k)
        good = [c for c in all_chunks if c.similarity >= SIMILARITY_THRESHOLD]
        is_fallback = len(good) == 0
        prompt = self._build_prompt(query, good, history)
        raw, ok = self._call_ollama(prompt, chunks=good)
        answer = (f"{FALLBACK_LABEL}\n\n{raw}" if is_fallback else raw)
        conf, cscore= self._confidence(good)
        return GeneratedResponse(
            answer=answer, source_refs=self._source_refs(good),
            is_fallback=is_fallback, model_used=OLLAMA_MODEL,
            top_chunks=good, confidence=conf, confidence_score=cscore)

if __name__ == "__main__":
    gen = LLMResponseGeneration()
    q = input("Question (Enter for default): ").strip() or \
          "What is Retrieval-Augmented Generation and how does it work?"
    print(f"\nQuery: {q}\n{'\u2500'*60}")
    r = gen.generate(q)
    print(f"Confidence: {r.confidence} ({r.confidence_score:.3f})")
    print(f"Fallback  : {r.is_fallback}")
    print("Sources:")
    for s in r.source_refs:
        print(f"  \u2022 {s['source_file']} p.{s['page']} [{s['topic']}] sim={s['similarity']}")
    print(f"\nAnswer:\n{r.answer}")