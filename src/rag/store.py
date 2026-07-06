"""Embedding store + similarity search on SQLite (numpy brute force).

At our scale (thousands of articles) exact brute-force cosine search is
faster and simpler than running a vector DB. Swap for one if N grows large.
"""
import numpy as np

from src import db
from src.embed import EMBED_MODEL, embed_texts

SCHEMA = """
CREATE TABLE IF NOT EXISTS article_embeddings (
    article_id INTEGER PRIMARY KEY REFERENCES articles(id),
    model      TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    vector     BLOB NOT NULL
);
"""


def init_store() -> None:
    with db.get_conn() as conn:
        conn.executescript(SCHEMA)


def index_new_articles(batch_limit: int = 500) -> int:
    """Embed articles that don't have vectors yet. Returns count indexed."""
    init_store()
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT a.id, a.title FROM articles a "
            "LEFT JOIN article_embeddings e ON e.article_id = a.id "
            "WHERE e.article_id IS NULL ORDER BY a.id LIMIT ?",
            (batch_limit,),
        ).fetchall()
    if not rows:
        return 0

    vectors = embed_texts([r["title"] for r in rows])
    with db.get_conn() as conn:
        for r, vec in zip(rows, vectors):
            v = np.asarray(vec, dtype=np.float32)
            conn.execute(
                "INSERT OR REPLACE INTO article_embeddings "
                "(article_id, model, dim, vector) VALUES (?, ?, ?, ?)",
                (r["id"], EMBED_MODEL, len(v), v.tobytes()),
            )
    return len(rows)


def search(query_vector: list[float], top_k: int = 8,
           since: str | None = None) -> list[dict]:
    """Cosine top-k over stored article vectors.

    since: optional UTC ISO date string to filter by collected_at.
    """
    sql = (
        "SELECT e.article_id, e.vector, a.title, a.url, a.source, a.market, "
        "a.published_at, a.collected_at "
        "FROM article_embeddings e JOIN articles a ON a.id = e.article_id"
    )
    params: tuple = ()
    if since:
        sql += " WHERE a.collected_at >= ?"
        params = (since,)

    with db.get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    M = np.frombuffer(b"".join(r["vector"] for r in rows), dtype=np.float32)
    M = M.reshape(len(rows), -1)
    M = M / np.linalg.norm(M, axis=1, keepdims=True)

    q = np.asarray(query_vector, dtype=np.float32)
    q = q / np.linalg.norm(q)

    scores = M @ q
    order = np.argsort(scores)[::-1][:top_k]
    return [
        {
            "score": float(scores[i]),
            "title": rows[i]["title"],
            "url": rows[i]["url"],
            "source": rows[i]["source"],
            "market": rows[i]["market"],
            "date": (rows[i]["published_at"] or rows[i]["collected_at"] or "")[:10],
        }
        for i in order
    ]
