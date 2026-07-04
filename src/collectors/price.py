"""Price collector via yfinance (KR + US + indices)."""
import yfinance as yf

from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US


def _fetch_ticker(ticker: str, name: str, market: str, period: str = "5d") -> list[dict]:
    rows = []
    try:
        hist = yf.Ticker(ticker).history(period=period)
        hist = hist.dropna(subset=["Close"])  # recent rows can contain NaN
        for date, row in hist.iterrows():
            rows.append({
                "market": market,
                "ticker": ticker,
                "name": name,
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })
    except Exception as exc:
        print(f"[price] {ticker} FAILED: {exc}")
    return rows


def collect_prices() -> list[dict]:
    """Fetch last 5 days of OHLCV for watchlists and indices.

    5-day window + INSERT OR IGNORE means missed days self-heal on the next run.
    """
    rows: list[dict] = []
    for ticker, name in WATCHLIST_KR.items():
        rows += _fetch_ticker(ticker, name, "KR")
    for ticker, name in WATCHLIST_US.items():
        rows += _fetch_ticker(ticker, name, "US")
    for ticker, name in INDICES.items():
        rows += _fetch_ticker(ticker, name, "INDEX")
    print(f"[price] {len(rows)} rows fetched")
    return rows
