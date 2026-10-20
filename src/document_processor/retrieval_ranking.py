"""Lexical evidence and reranking within an already authorised course."""
from collections import Counter
import math
import re

_STOP = set("a an the is are was were be been being to of for in on at by with from "
            "and or as it its this that these those what which who when where how "
            "do does did can could should would will we us our i me my you your "
            "please tell explain about give ask asks asked question questions many "
            "worth overall not".split())


def _tokens(text):
    tokens = [t for t in re.findall(r"\b\w+\b", text.lower().replace("_", " "))
              if t not in _STOP]
    return [t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith(("ss", "us", "is"))
            else t for t in tokens]


def expand_assessment_reference(query):
    """Expand common A-number shorthand only in an assessment-related question."""
    if re.search(r"\b(?:assignment|assessment|marks?|worth|submit|submission|due)\b", query, re.I):
        return re.sub(r"\bA(\d{1,2})\b", r"Assignment \1", query, flags=re.I)
    return query


def _lexical_scores(query, texts):
    query_terms = set(_tokens(query))
    terms = [Counter(_tokens(text)) for text in texts]
    lengths = [sum(t.values()) for t in terms]
    average = sum(lengths) / max(len(lengths), 1) or 1
    counts = Counter(word for tokens in terms for word in tokens)
    scores, supported = [], []
    for tokens, length in zip(terms, lengths):
        score = 0.0
        for word in query_terms:
            tf = tokens[word]
            if not tf:
                continue
            df = counts[word]
            idf = math.log(1 + (len(terms) - df + .5) / (df + .5))
            score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average))
        scores.append(score)
        matched = query_terms & tokens.keys()
        rare = any(counts[t] <= max(1, len(terms) * .1) for t in matched)
        numbers = {t for t in query_terms if t.isdigit()}
        supported.append(len(matched) >= 2 and len(matched) >= len(query_terms) * .5
                         and rare and numbers <= matched)
    return scores, supported


def lexical_candidates(query, texts, limit=8):
    """Require multiple query terms, majority coverage and a discriminating term."""
    scores, supported = _lexical_scores(query, texts)
    return sorted((i for i in range(len(texts)) if supported[i]),
                  key=lambda i: scores[i], reverse=True)[:limit]


def rerank(query, chunks, threshold):
    """Blend BM25 with cosine similarity without altering the reported score.

    Low-similarity hits need independently established lexical support.
    Images with sparse text remain available as diagnostics, after usable text.
    """
    if not chunks:
        return []
    scores, _ = _lexical_scores(query, [c.text for c in chunks])
    maximum = max(scores) or 1
    def key(index):
        ch = chunks[index]
        usable = getattr(ch, "text_quality", "") != "image_text_sparse"
        eligible = ch.similarity >= threshold or getattr(ch, "lexical_match", False)
        score = .75 * ch.similarity + (.25 * scores[index] / maximum if eligible else 0)
        return usable, eligible, score
    return [chunks[i] for i in sorted(range(len(chunks)), key=key, reverse=True)]
