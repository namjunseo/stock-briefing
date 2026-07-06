"""Index unembedded articles into the RAG store.

Usage:
    python index.py
"""
from src import db
from src.rag.store import index_new_articles


def main() -> None:
    db.init_db()
    total = 0
    while True:
        n = index_new_articles()
        total += n
        if n == 0:
            break
        print(f"indexed {n} articles...")
    print(f"done. {total} new articles indexed.")


if __name__ == "__main__":
    main()
