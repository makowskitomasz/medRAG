"""RAG evaluation metrics — no RAGAS dependency."""

import re
import string

# ── Text normalisation ────────────────────────────────────────────────────────


# Kept in sync with generation's citation_extractor.CITATION_RX — models pad the
# marker with markdown emphasis or zero-width characters, and a leftover marker
# would otherwise be scored as answer content.
_PAD = r"[\s*_~`​‌‍⁠﻿]*"
_CITATION_RX = re.compile(
    rf"[\[(【]{_PAD}SOURCE{_PAD}[-_\s]?{_PAD}\d+{_PAD}[\])】]",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    text = _CITATION_RX.sub("", text)
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def _tokenise(text: str) -> list[str]:
    return _normalise(text).split()


# ── Token-level F1 ────────────────────────────────────────────────────────────


def token_f1(prediction: str, gold: str) -> float:
    from collections import Counter

    pred_tokens = _tokenise(prediction)
    gold_tokens = _tokenise(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    n_common = sum(common.values())
    if n_common == 0:
        return 0.0
    precision = n_common / len(pred_tokens)
    recall = n_common / len(gold_tokens)
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


def rouge_l(prediction: str, gold: str) -> float:
    """ROUGE-L: F1 based on longest common subsequence of tokens."""
    pred_tokens = _tokenise(prediction)
    gold_tokens = _tokenise(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0

    m, n = len(gold_tokens), len(pred_tokens)
    # LCS via DP — O(m*n) but inputs are short answers
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if gold_tokens[i - 1] == pred_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    if lcs == 0:
        return 0.0
    precision = lcs / n
    recall = lcs / m
    return 2 * precision * recall / (precision + recall)


def context_recall(
    retrieved_filenames: list[str],
    gold_context_titles: list[str],
) -> float:
    """Fraction of gold supporting documents found in retrieved chunks.

    Matches by normalised slug: lowercase, non-alphanumeric → underscore.
    """
    if not gold_context_titles:
        return 0.0

    def _slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    retrieved_slugs = {_slug(f.replace(".txt", "")) for f in retrieved_filenames if f}
    hits = sum(1 for title in gold_context_titles if _slug(title) in retrieved_slugs)
    return hits / len(gold_context_titles)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    import numpy as np

    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
