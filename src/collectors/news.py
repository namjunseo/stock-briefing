"""RSS news collector."""
import calendar
from datetime import datetime, timezone

import feedparser
import requests

from src.config import HTTP_HEADERS, RSS_FEEDS


def _to_utc_iso(published_parsed) -> str | None:
    """feedparser gives a UTC struct_time; convert to ISO string."""
    if not published_parsed:
        return None
    ts = calendar.timegm(published_parsed)
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def collect_news() -> list[dict]:
    """Fetch all configured RSS feeds. A failing feed is logged and skipped."""
    rows = []
    for feed_cfg in RSS_FEEDS:
        try:
            r = requests.get(feed_cfg["url"], headers=HTTP_HEADERS, timeout=10)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            for e in feed.entries:
                if not e.get("link") or not e.get("title"):
                    continue  # skip malformed entries
                rows.append({
                    "market": feed_cfg["market"],
                    "source": feed_cfg["source"],
                    "title": e.title.strip(),
                    "url": e.link.strip(),
                    "published_at": _to_utc_iso(e.get("published_parsed")),
                })
            print(f"[news] {feed_cfg['source']}: {len(feed.entries)} entries")
        except Exception as exc:
            print(f"[news] {feed_cfg['source']} FAILED: {exc}")
    return rows
