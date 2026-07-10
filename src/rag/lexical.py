"""BM25 lexical search over article titles.

Korean is tokenized as character bigrams (no morphological analyzer needed
at this scale); ASCII words/numbers are kept as-is.
"""
import re

import numpy as np
from rank_bm25 import BM25Okapi

from src import db


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for word in re.findall(r"[가-힣]+", text):  # bigrams within each word only
        if len(word) == 1:
            tokens.append(word)
        else:
            tokens += [word[i : i + 2] for i in range(len(word) - 1)]
    return tokens


class LexicalIndex:
    """In-memory BM25 index built from the articles table."""

    def __init__(self) -> None:
        with db.get_conn() as conn:
            rows = conn.execute("SELECT id, title FROM articles ORDER BY id").fetchall()
        self.ids = [r["id"] for r in rows]
        self._bm25 = BM25Okapi([tokenize(r["title"]) for r in rows]) if rows else None

    def rank(self, query: str, top_k: int = 20) -> list[int]:
        """Article ids ranked by BM25 score (zero-score results excluded)."""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        order = np.argsort(scores)[::-1][:top_k]
        return [self.ids[i] for i in order if scores[i] > 0]
