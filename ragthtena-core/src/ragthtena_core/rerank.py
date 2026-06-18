import sys

_reranker = None
_log_tag = "[ragthtena]"


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def rerank(query: str, passages: list[dict], top_k: int) -> list[dict]:
    if not passages:
        return passages
    try:
        model = _get_reranker()
    except Exception:
        print(f"{_log_tag} WARNING: Reranker unavailable — using raw vector results.",
              file=sys.stderr)
        return passages[:top_k]
    pairs = [[query, p["text"]] for p in passages]
    scores = model.predict(pairs, show_progress_bar=False)
    import numpy as np
    for p, score in zip(passages, scores):
        p["relevance"] = round(float(1 / (1 + np.exp(-score))), 4)
    passages.sort(key=lambda x: x["relevance"], reverse=True)
    return passages[:top_k]
