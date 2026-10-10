# Authors: Thi Hong Ngoc Nguyen, Thanh Binh Tran
import re
import math
import warnings
from typing import List

DIM = 384

# Common English stopwords to skip (reduce noise)
_STOPWORDS = frozenset({
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","shall","should","may","might",
    "must","can","could","this","that","these","those","it","its","as","if",
    "so","than","then","when","where","who","which","what","how","not","no",
    "into","up","out","more","also","each","such","any","all","very","just",
    "their","they","them","there","we","our","us","you","your","i","my","me",
    "he","she","him","her","his","its","been","only","other","about",
})

_OFFLINE_WARNING = """\
OfflineEmbedder ACTIVE – DEGRADED RETRIEVAL QUALITY
sentence-transformers is not installed or failed to load.
The FNV-1a hash embedder is a keyword-overlap approximation only.
Semantic similarity scores will be unreliable.
To restore full quality: 
pip install sentence-transformers 
"""

def _fnv1a_hash(text: str) -> int:
    """FNV-1a 32-bit hash – fast, low collision, deterministic."""
    h = 2166136261
    for ch in text.encode("utf-8", errors="replace"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def _tokenise(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9_\-]{2,}", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


def embed(text: str, dim: int = DIM) -> List[float]:
    tokens = _tokenise(text)
    if not tokens:
        return [0.0] * dim

    vec = [0.0] * dim

    # Unigrams (weighted by inverse position)
    for i, tok in enumerate(tokens):
        pos_weight = 1.0 / math.log(i + 2)          # log-dampen position
        h = _fnv1a_hash(tok)
        idx = h % dim
        sign = 1.0 if (h >> 16) & 1 else -1.0       # ±1 sign flip
        vec[idx] += sign * pos_weight

    # Bigrams (capture short phrases)
    for i in range(len(tokens) - 1):
        bigram = tokens[i] + "_" + tokens[i + 1]
        h = _fnv1a_hash(bigram)
        idx = h % dim
        sign = 1.0 if (h >> 16) & 1 else -1.0
        vec[idx] += sign * 0.5                        # half-weight bigrams

    # L2 normalise
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]

    return vec


def embed_batch(texts: List[str], dim: int = DIM) -> List[List[float]]:
    """Embed a list of texts."""
    return [embed(t, dim) for t in texts]


class OfflineEmbedder:
    """
    Drop-in replacement for SentenceTransformer in offline / no-dependency
    environments.  Prints a prominent warning on first instantiation so the
    operator knows retrieval quality is degraded.
    """

    MODEL_NAME = "all-MiniLM-L6-v2-offline"
    _warned    = False   # class-level flag – warn once per process

    def __init__(self):
        if not OfflineEmbedder._warned:
            print(_OFFLINE_WARNING, flush=True)
            warnings.warn(
                "OfflineEmbedder active: retrieval quality is degraded. "
                "Install sentence-transformers for production use.",
                RuntimeWarning,
                stacklevel=2,
            )
            OfflineEmbedder._warned = True

    def encode(self, text_or_texts, normalize_embeddings: bool = True) -> List:
        if isinstance(text_or_texts, str):
            return embed(text_or_texts)
        return embed_batch(text_or_texts)

    def get_sentence_embedding_dimension(self) -> int:
        return DIM
    
    # Alias for newer sentence-transformers API compatibility
    def get_embedding_dimension(self) -> int:
        return DIM


if __name__ == "__main__":
    e = OfflineEmbedder()
    v1 = e.encode("Retrieval-Augmented Generation uses dense retrieval")
    v2 = e.encode("RAG combines retrieval with a language model")
    v3 = e.encode("The best chocolate cake recipe uses butter and sugar")

    def cosine(a, b):
        return sum(x * y for x, y in zip(a, b))
    
    print(f"RAG vs RAG-like  : {cosine(v1,v2):.4f}  (should be high)")
    print(f"RAG vs cake      : {cosine(v1,v3):.4f}  (should be low)")
    print(f"Vector length    : {len(v1)}")
