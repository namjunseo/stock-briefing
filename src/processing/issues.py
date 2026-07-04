"""Extract 'issues of the day' by clustering recent article titles."""
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from src import db

# Cosine distance threshold: lower = stricter clusters. Tune on real data.
DISTANCE_THRESHOLD = 0.35


def load_recent_articles(hours: int = 24) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, market, source, title, url FROM articles "
            "WHERE collected_at >= ? ORDER BY id",
            (since,),
        ).fetchall()
    return [dict(r) for r in rows]


def cluster_titles(vectors: list[list[float]]) -> np.ndarray:
    """Cluster embedding vectors; returns a cluster label per vector."""
    X = np.asarray(vectors, dtype=np.float32)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)  # normalize for cosine
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=DISTANCE_THRESHOLD,
        metric="cosine",
        linkage="average",
    )
    return clustering.fit_predict(X)


def top_issues(articles: list[dict], labels: np.ndarray, vectors: list[list[float]],
               top_n: int = 5, min_size: int = 2) -> list[dict]:
    """Rank clusters by size; representative = article closest to cluster centroid."""
    X = np.asarray(vectors, dtype=np.float32)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)

    issues = []
    for label in set(labels):
        idx = np.where(labels == label)[0]
        if len(idx) < min_size:  # singletons are noise, not "issues"
            continue
        centroid = X[idx].mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        rep_i = idx[np.argmax(X[idx] @ centroid)]
        issues.append({
            "size": int(len(idx)),
            "representative": articles[rep_i]["title"],
            "articles": [articles[i] for i in idx],
        })
    issues.sort(key=lambda x: x["size"], reverse=True)
    return issues[:top_n]
