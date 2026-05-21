"""RAG evaluation metrics — no RAGAS dependency."""

import string

# ── Text normalisation ────────────────────────────────────────────────────────


def _normalise(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def _tokenise(text: str) -> list[str]:
    return _normalise(text).split()


# ── Token-level F1 ────────────────────────────────────────────────────────────


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = _tokenise(prediction)
    gold_tokens = _tokenise(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


# ── Exact Match ───────────────────────────────────────────────────────────────


def exact_match(prediction: str, gold: str) -> float:
    return 1.0 if _normalise(prediction) == _normalise(gold) else 0.0


# ── Citation precision ────────────────────────────────────────────────────────


def citation_precision(n_citations: int, top_k: int) -> float:
    if top_k <= 0:
        return 0.0
    return min(1.0, n_citations / top_k)


# ── Cosine similarity (numpy) ─────────────────────────────────────────────────


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    import numpy as np

    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
