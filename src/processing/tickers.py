"""Dictionary-based ticker mapping: find watchlist companies mentioned in titles."""
from src.config import WATCHLIST_KR, WATCHLIST_US

# Extra aliases beyond the official names in config.
# "exclude": if any of these substrings is present around the match context,
# the alias alone is too ambiguous -> skip (e.g. 메타버스 vs 메타).
ALIASES: dict[str, list[dict]] = {
    "005930.KS": [{"alias": "삼성전자"}, {"alias": "삼전"}],
    "000660.KS": [{"alias": "SK하이닉스"}, {"alias": "하이닉스"}, {"alias": "삼전닉스"}],
    "373220.KS": [{"alias": "LG에너지솔루션"}, {"alias": "LG엔솔"}],
    "207940.KS": [{"alias": "삼성바이오로직스"}, {"alias": "삼바"}],
    "005380.KS": [{"alias": "현대차"}, {"alias": "현대자동차"}],
    "051910.KS": [{"alias": "LG화학"}],
    "035420.KS": [{"alias": "네이버"}, {"alias": "NAVER"}],
    "035720.KS": [{"alias": "카카오"}],
    "005490.KS": [{"alias": "포스코홀딩스"}, {"alias": "POSCO홀딩스"}, {"alias": "포스코"}],
    "105560.KS": [{"alias": "KB금융"}],
    "AAPL": [{"alias": "애플"}, {"alias": "Apple"}],
    "MSFT": [{"alias": "마이크로소프트"}],
    "NVDA": [{"alias": "엔비디아"}, {"alias": "NVIDIA"}],
    "GOOGL": [{"alias": "알파벳"}, {"alias": "구글"}],
    "AMZN": [{"alias": "아마존"}],
    "TSLA": [{"alias": "테슬라"}],
    "META": [{"alias": "메타", "exclude": ["메타버스"]}, {"alias": "Meta"}],
}

_NAMES = {**WATCHLIST_KR, **WATCHLIST_US}


def find_tickers(text: str) -> list[str]:
    """Return watchlist tickers mentioned in the text."""
    found = []
    for ticker, alias_list in ALIASES.items():
        for a in alias_list:
            if a["alias"] not in text:
                continue
            if any(ex in text for ex in a.get("exclude", [])):
                continue
            found.append(ticker)
            break  # one match per ticker is enough
    return found


def map_issue_tickers(issue: dict) -> list[dict]:
    """Aggregate ticker mentions across all articles of an issue.

    Returns [{"ticker", "name", "mentions"}] sorted by mention count.
    """
    counts: dict[str, int] = {}
    for article in issue["articles"]:
        for ticker in find_tickers(article["title"]):
            counts[ticker] = counts.get(ticker, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {"ticker": t, "name": _NAMES.get(t, t), "mentions": c}
        for t, c in ranked
    ]
