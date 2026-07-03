"""Smoke test: check all 4 data sources are reachable.

Usage:
    python test_sources.py

Requires .env with DART_API_KEY (see README).
"""
import os
from datetime import datetime, timedelta

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()


def test_rss():
    # Hankyung (Korea Economic Daily) official securities RSS
    # NOTE: server rejects feedparser's default User-Agent -> fetch manually
    url = "https://www.hankyung.com/feed/finance"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    r = requests.get(url, headers=headers, timeout=10)
    feed = feedparser.parse(r.content)
    assert len(feed.entries) > 0, f"no entries (status {r.status_code})"
    print(f"[OK] RSS: {len(feed.entries)} articles, latest: {feed.entries[0].title[:40]}")


def test_price_kr():
    import yfinance as yf

    hist = yf.Ticker("005930.KS").history(period="5d")  # Samsung Elec (KOSPI)
    close = hist["Close"].dropna()  # recent rows can contain NaN
    assert len(close) > 0, "no valid close price"
    print(f"[OK] yfinance KR: Samsung close = {close.iloc[-1]:,.0f}")


def test_price_us():
    import yfinance as yf

    hist = yf.Ticker("^GSPC").history(period="5d")  # S&P 500
    close = hist["Close"].dropna()
    assert len(close) > 0, "no valid close price"
    print(f"[OK] yfinance US: S&P500 close = {close.iloc[-1]:,.2f}")


def test_dart():
    key = os.environ["DART_API_KEY"]
    url = "https://opendart.fss.or.kr/api/list.json"
    # default (no date) queries today only -> 0 results on weekends/holidays
    bgn_de = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    r = requests.get(
        url,
        params={"crtfc_key": key, "bgn_de": bgn_de, "page_count": 5},
        timeout=10,
    )
    data = r.json()
    assert data["status"] == "000", f"DART error: {data}"
    print(f"[OK] DART: {len(data['list'])} recent disclosures")


def test_edgar():
    url = "https://data.sec.gov/submissions/CIK0000320193.json"  # Apple
    headers = {"User-Agent": "stock-briefing namjunseo051219@gmail.com"}
    r = requests.get(url, headers=headers, timeout=10)
    assert r.status_code == 200, f"status {r.status_code}"
    print(f"[OK] EDGAR: fetched filings for {r.json()['name']}")


if __name__ == "__main__":
    for test in [test_rss, test_price_kr, test_price_us, test_dart, test_edgar]:
        try:
            test()
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
