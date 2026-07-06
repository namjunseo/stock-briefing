"""SEC EDGAR disclosure collector (US watchlist companies)."""
import time
from datetime import datetime, timedelta

import requests

from src.config import EDGAR_FORMS, EDGAR_USER_AGENT, WATCHLIST_US

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
HEADERS = {"User-Agent": EDGAR_USER_AGENT}


def _load_cik_map() -> dict[str, int]:
    """ticker -> CIK for all SEC-registered companies."""
    r = requests.get(TICKER_MAP_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return {v["ticker"]: v["cik_str"] for v in r.json().values()}


def filter_recent_filings(recent: dict, since: str) -> list[dict]:
    """Pick briefing-worthy forms filed on/after `since` (YYYY-MM-DD).

    `recent` is EDGAR's parallel-array structure:
    {"form": [...], "filingDate": [...], "accessionNumber": [...]}
    """
    out = []
    for form, date, accno in zip(
        recent.get("form", []), recent.get("filingDate", []),
        recent.get("accessionNumber", []),
    ):
        if form in EDGAR_FORMS and date >= since:
            out.append({"form": form, "filingDate": date, "accessionNumber": accno})
    return out


def collect_edgar(days: int = 3) -> list[dict]:
    """Fetch recent filings for all US watchlist companies."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        cik_map = _load_cik_map()
    except Exception as exc:
        print(f"[edgar] FAILED to load ticker map: {exc}")
        return []

    rows: list[dict] = []
    for ticker, name in WATCHLIST_US.items():
        cik = cik_map.get(ticker)
        if cik is None:
            print(f"[edgar] no CIK for {ticker} (skipped)")
            continue
        try:
            r = requests.get(SUBMISSIONS_URL.format(cik=cik), headers=HEADERS, timeout=15)
            r.raise_for_status()
            recent = r.json().get("filings", {}).get("recent", {})
        except Exception as exc:
            print(f"[edgar] {ticker} FAILED: {exc}")
            continue

        for f in filter_recent_filings(recent, since):
            rows.append({
                "market": "US",
                "corp_name": name,  # our watchlist name -> same filter as KR
                "title": f["form"],
                "rcept_no": f["accessionNumber"],
                "disclosed_at": f["filingDate"],
            })
        time.sleep(0.15)  # SEC fair-use guideline (<10 req/s)

    print(f"[edgar] {len(rows)} filings since {since}")
    return rows
