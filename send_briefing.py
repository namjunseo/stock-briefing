"""Generate today's briefing and send it by email.

Usage:
    python send_briefing.py            # generate + send
    python send_briefing.py --dry-run  # save briefing.html locally, don't send
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from src import db
from src.briefing import get_price_changes, get_watchlist_disclosures, render_html
from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US
from src.embed import embed_texts
from src.mailer import send_html
from src.processing.issues import cluster_titles, load_recent_articles, top_issues
from src.processing.tickers import map_issue_tickers
from src.summarize import summarize_issue

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def build_issues(hours: int = 24) -> list[dict]:
    articles = load_recent_articles(hours=hours)
    print(f"{len(articles)} articles in the last {hours}h")
    if len(articles) < 3:
        return []  # briefing still goes out with prices/disclosures only

    vectors = embed_texts([a["title"] for a in articles])
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

    issues = build_issues()
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
