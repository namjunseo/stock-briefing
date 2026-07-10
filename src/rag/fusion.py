"""Reciprocal Rank Fusion of multiple ranked lists."""


def rrf_fuse(rank_lists: list[list[int]], k: int = 60, top_k: int = 10) -> list[int]:
    """Fuse ranked id lists: score(id) = sum over lists of 1/(k + rank).

    k=60 is the standard damping constant from the original RRF paper.
    """
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for rank, id_ in enumerate(ranks, start=1):
            scores[id_] = scores.get(id_, 0.0) + 1.0 / (k + rank)
    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [id_ for id_, _ in ordered[:top_k]]
