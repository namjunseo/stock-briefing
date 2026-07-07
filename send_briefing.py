"""Generate today's briefing and send it by email.

Reuses embeddings stored by index.py instead of re-embedding (cheaper,
and immune to embedding-quota failures). If issue extraction fails for
any reason, the briefing still goes out with prices/disclosures only.

Usage:
    python send_briefing.py            # generate + send
    python send_briefing.py --dry-run  # save briefing.html locally, don't send
"""
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from src import db
from src.briefing import get_price_changes, get_watchlist_disclosures, render_html
from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US
from src.mailer import send_html
from src.processing.issues import cluster_titles, top_issues
from src.processing.tickers import map_issue_tickers
from src.rag.store import get_recent_articles_with_vectors
from src.summarize import summarize_issue

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def build_issues(hours: int = 24) -> list[dict]:
    articles, vectors = get_recent_articles_with_vectors(hours=hours)
    print(f"{len(articles)} indexed articles in the last {hours}h")
    if len(articles) < 3:
        return []

    labels = cluster_titles(vectors)
    issues = top_issues(articles, labels, vectors)
    for issue in issues:
        issue["tickers"] = map_issue_tickers(issue)
        issue["summary"] = summarize_issue(issue)
    return issues


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    db.init_db()

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    date_str = f"{now.strftime('%Y-%m-%d')} ({WEEKDAY_KR[now.weekday()]})"

    # Graceful degradation: never let issue extraction kill the briefing.
    try:
        issues = build_issues()
    except Exception:
        print("[warn] issue extraction failed; sending without issues")
        traceback.print_exc()
        issues = []

    html = render_html(
        date_str=date_str,
        issues=issues,
        kr_prices=get_price_changes(WATCHLIST_KR),
        us_prices=get_price_changes(WATCHLIST_US),
        index_prices=get_price_changes(INDICES),
        disclosures=get_watchlist_disclosures(),
    )

    if dry_run:
        with open("briefing.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("dry run: saved to briefing.html (open it in a browser)")
        return

    send_html(subject=f"[주식 브리핑] {date_str}", html=html)
    print("briefing sent.")


if __name__ == "__main__":
    main()
