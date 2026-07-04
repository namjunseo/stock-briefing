"""Extract today's top issues, map tickers, and summarize each issue.

Usage:
    python analyze.py [hours]   # default: last 24 hours
"""
import sys

from src import db
from src.embed import embed_texts
from src.processing.issues import cluster_titles, load_recent_articles, top_issues
from src.processing.tickers import map_issue_tickers
from src.summarize import summarize_issue


def main() -> None:
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24

    db.init_db()  # ensure new llm_calls table exists

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
        tickers = map_issue_tickers(issue)
        summary = summarize_issue(issue)

        ticker_str = ", ".join(f"{t['name']}({t['mentions']})" for t in tickers) or "-"
        print(f"\n#{rank} [{issue['size']} articles] {issue['representative']}")
        print(f"  요약: {summary}")
        print(f"  관련 종목: {ticker_str}")

    # usage report for this run
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, SUM(input_tokens) AS ti, SUM(output_tokens) AS to_, "
            "AVG(latency_ms) AS lat FROM llm_calls "
            "WHERE created_at >= datetime('now', '-5 minutes')"
        ).fetchone()
    if row["n"]:
        print(f"\n[usage] {row['n']} LLM calls, tokens in/out = {row['ti']}/{row['to_']}, "
              f"avg latency = {row['lat']:.0f}ms")


if __name__ == "__main__":
    main()
