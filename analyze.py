"""Extract and print today's top issues from collected news.

Usage:
    python analyze.py [hours]   # default: last 24 hours
"""
import sys

from src.embed import embed_texts
from src.processing.issues import cluster_titles, load_recent_articles, top_issues


def main() -> None:
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24

    articles = load_recent_articles(hours=hours)
    print(f"{len(articles)} articles in the last {hours}h")
    if len(articles) < 3:
        print("Not enough articles to cluster. Run collect.py first or widen the window.")
        return

    print("embedding titles...")
    vectors = embed_texts([a["title"] for a in articles])

    labels = cluster_titles(vectors)
    issues = top_issues(articles, labels, vectors)

    print(f"\n=== Top issues ({len(issues)}) ===")
    for rank, issue in enumerate(issues, 1):
        print(f"\n#{rank} [{issue['size']} articles] {issue['representative']}")
        for a in issue["articles"][:5]:
            print(f"    - ({a['source']}) {a['title'][:60]}")


if __name__ == "__main__":
    main()
