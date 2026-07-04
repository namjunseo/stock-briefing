"""Build the daily briefing HTML.

Design rule (hallucination control): every number in the briefing
(prices, changes, disclosure titles) is inserted directly from the DB.
The LLM only writes issue summaries.
"""
from src import db
from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US

UP = "#d24f45"    # red = up (KR convention)
DOWN = "#1261c4"  # blue = down
GRAY = "#666666"


def get_price_changes(tickers: dict[str, str]) -> list[dict]:
    """Latest close + change vs previous close for each ticker."""
    out = []
    with db.get_conn() as conn:
        for ticker, name in tickers.items():
            rows = conn.execute(
                "SELECT date, close FROM prices WHERE ticker = ? "
                "ORDER BY date DESC LIMIT 2",
                (ticker,),
            ).fetchall()
            if not rows:
                continue  # no data yet for this ticker
            latest = rows[0]
            change_pct = None
            if len(rows) == 2 and rows[1]["close"]:
                change_pct = (latest["close"] - rows[1]["close"]) / rows[1]["close"] * 100
            out.append({
                "ticker": ticker,
                "name": name,
                "date": latest["date"],
                "close": latest["close"],
                "change_pct": change_pct,
            })
    return out


def get_watchlist_disclosures(limit: int = 10) -> list[dict]:
    """Recent disclosures of watchlist companies only."""
    names = tuple(WATCHLIST_KR.values())
    placeholders = ",".join("?" * len(names))
    with db.get_conn() as conn:
        rows = conn.execute(
            f"SELECT corp_name, title, disclosed_at FROM disclosures "
            f"WHERE corp_name IN ({placeholders}) "
            f"ORDER BY disclosed_at DESC, id DESC LIMIT ?",
            (*names, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def _fmt_change(pct: float | None) -> str:
    if pct is None:
        return f'<span style="color:{GRAY}">-</span>'
    color = UP if pct > 0 else DOWN if pct < 0 else GRAY
    sign = "+" if pct > 0 else ""
    return f'<span style="color:{color};font-weight:bold">{sign}{pct:.2f}%</span>'


def _price_table(rows: list[dict], price_fmt: str = "{:,.0f}") -> str:
    tr = ""
    for r in rows:
        tr += (
            f'<tr><td style="padding:4px 8px">{r["name"]}</td>'
            f'<td style="padding:4px 8px;text-align:right">{price_fmt.format(r["close"])}</td>'
            f'<td style="padding:4px 8px;text-align:right">{_fmt_change(r["change_pct"])}</td></tr>'
        )
    return (
        '<table style="border-collapse:collapse;font-size:14px">'
        '<tr style="color:#999;font-size:12px"><td style="padding:4px 8px">종목</td>'
        '<td style="padding:4px 8px;text-align:right">종가</td>'
        '<td style="padding:4px 8px;text-align:right">등락</td></tr>'
        f"{tr}</table>"
    )


def _section(title: str, body: str) -> str:
    return (
        f'<h2 style="font-size:16px;border-bottom:2px solid #333;'
        f'padding-bottom:4px;margin:24px 0 8px">{title}</h2>{body}'
    )


def render_html(date_str: str, issues: list[dict], kr_prices: list[dict],
                us_prices: list[dict], index_prices: list[dict],
                disclosures: list[dict]) -> str:
    # --- issues section ---
    issue_html = ""
    for rank, it in enumerate(issues, 1):
        tickers = ", ".join(f"{t['name']}" for t in it.get("tickers", [])) or "-"
        links = " · ".join(
            f'<a href="{a["url"]}" style="color:#888;text-decoration:none">기사{i+1}</a>'
            for i, a in enumerate(it["articles"][:3])
        )
        issue_html += (
            f'<div style="margin-bottom:16px">'
            f'<div style="font-weight:bold;font-size:15px">#{rank} {it["representative"]}'
            f' <span style="color:#999;font-weight:normal;font-size:12px">({it["size"]}건)</span></div>'
            f'<div style="font-size:14px;margin:4px 0">{it.get("summary", "")}</div>'
            f'<div style="font-size:12px;color:#666">관련 종목: {tickers} &nbsp;|&nbsp; {links}</div>'
            f"</div>"
        )
    if not issue_html:
        issue_html = '<div style="font-size:14px;color:#999">수집된 뉴스가 부족합니다.</div>'

    # --- disclosures section ---
    disc_html = "".join(
        f'<li style="font-size:13px;margin-bottom:4px">'
        f'<b>{d["corp_name"]}</b> {d["title"]} '
        f'<span style="color:#999">({d["disclosed_at"]})</span></li>'
        for d in disclosures
    )
    disc_html = f'<ul style="padding-left:20px;margin:4px 0">{disc_html}</ul>' if disc_html \
        else '<div style="font-size:13px;color:#999">관심종목 신규 공시 없음</div>'

    body = (
        _section("오늘의 이슈", issue_html)
        + _section("간밤 미국 시장", _price_table(index_prices, "{:,.2f}") + "<br>"
                   + _price_table(us_prices, "{:,.2f}"))
        + _section("국내 관심종목", _price_table(kr_prices))
        + _section("관심종목 공시", disc_html)
    )

    return (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;'
        'max-width:600px;margin:0 auto;padding:16px">'
        f'<h1 style="font-size:20px">📈 주식 데일리 브리핑 <span style="color:#999;'
        f'font-size:14px;font-weight:normal">{date_str}</span></h1>'
        f"{body}"
        '<p style="font-size:11px;color:#aaa;margin-top:24px">'
        "본 메일은 자동 생성된 정보 요약이며 투자 권유가 아닙니다. "
        "시세·공시는 수집 데이터 기준으로 실제와 차이가 있을 수 있습니다.</p>"
        "</div>"
    )
