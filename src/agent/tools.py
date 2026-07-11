"""Tools the agent can call. All numbers come straight from the DB."""
from src import db
from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US
from src.embed import embed_texts
from src.processing.tickers import find_tickers
from src.rag.store import search as vector_search

_INDEX_NAMES = {
    "코스피": "^KS11", "kospi": "^KS11",
    "코스닥": "^KQ11", "kosdaq": "^KQ11",
    "나스닥": "^IXIC", "nasdaq": "^IXIC",
    "s&p500": "^GSPC", "s&p": "^GSPC", "에스앤피": "^GSPC",
    "환율": "USDKRW=X", "원달러": "USDKRW=X", "달러": "USDKRW=X",
}
_ALL_NAMES = {**WATCHLIST_KR, **WATCHLIST_US, **INDICES}


def _resolve_ticker(name: str) -> str | None:
    raw = name.strip()
    if raw in _ALL_NAMES:  # already a ticker
        return raw
    low = raw.lower()
    for key, ticker in _INDEX_NAMES.items():
        if key in low:
            return ticker
    hits = find_tickers(raw)
    return hits[0] if hits else None


def get_price(name: str) -> dict:
    """종목이나 지수의 최신 종가와 전일 대비 등락률을 조회한다.

    Args:
        name: 회사명, 티커, 또는 지수명. 예: '삼성전자', 'NVDA', '코스피', '환율'
    """
    print(f"  [tool] get_price({name!r})")
    ticker = _resolve_ticker(name)
    if ticker is None:
        return {"error": f"'{name}'은(는) 관심종목/지수 목록에 없어 시세를 조회할 수 없음"}

    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT date, close FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 2",
            (ticker,),
        ).fetchall()
    if not rows:
        return {"error": f"{ticker}의 시세 데이터가 아직 없음"}

    out = {
        "name": _ALL_NAMES.get(ticker, ticker),
        "ticker": ticker,
        "date": rows[0]["date"],
        "close": rows[0]["close"],
    }
    if len(rows) == 2 and rows[1]["close"]:
        out["change_pct"] = round(
            (rows[0]["close"] - rows[1]["close"]) / rows[1]["close"] * 100, 2)
    return out


def search_news(query: str) -> list[dict]:
    """수집된 국내·미국 뉴스 기사에서 질의와 관련된 기사를 검색한다.

    Args:
        query: 검색할 주제나 질문. 예: 'SK하이닉스 ADR 상장'
    """
    print(f"  [tool] search_news({query!r})")
    q_vec = embed_texts([query])[0]
    hits = vector_search(q_vec, top_k=8)
    return [
        {"title": h["title"], "date": h["date"], "source": h["source"], "url": h["url"]}
        for h in hits
    ]


def get_disclosures(company: str) -> list[dict]:
    """특정 회사의 최근 공시 목록을 조회한다 (국내 DART + 미국 EDGAR).

    Args:
        company: 회사명. 예: '삼성전자', '애플'
    """
    print(f"  [tool] get_disclosures({company!r})")
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT corp_name, title, disclosed_at, market FROM disclosures "
            "WHERE corp_name LIKE ? ORDER BY disclosed_at DESC, id DESC LIMIT 10",
            (f"%{company.strip()}%",),
        ).fetchall()
    if not rows:
        return [{"info": f"'{company}'의 최근 공시 없음"}]
    return [dict(r) for r in rows]


AGENT_TOOLS = [get_price, search_news, get_disclosures]
