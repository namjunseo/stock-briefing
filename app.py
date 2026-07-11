"""Streamlit demo: tool-calling agent chat + data dashboard.

Local run:
    streamlit run app.py

On Hugging Face Spaces the DB is bootstrapped from the GitHub repo
(committed daily by GitHub Actions), so the demo stays fresh without
its own collector.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)

import pandas as pd
import requests
import streamlit as st

DB_RAW_URL = "https://github.com/namjunseo/stock-briefing/raw/main/stock_briefing.db"
DB_MAX_AGE_S = 6 * 3600

st.set_page_config(page_title="주식 데일리 브리핑", page_icon="📈", layout="wide")


def ensure_db() -> None:
    """Download the daily-updated DB from GitHub if missing or stale."""
    path = "stock_briefing.db"
    fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path)) < DB_MAX_AGE_S
    if fresh:
        return
    try:
        r = requests.get(DB_RAW_URL, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    except Exception as e:  # keep an old local copy if download fails
        if not os.path.exists(path):
            st.error(f"DB를 내려받지 못했습니다: {e}")
            st.stop()


ensure_db()

from src import db  # noqa: E402  (after ensure_db on purpose)
from src.agent.agent import Agent  # noqa: E402

db.init_db()

st.title("📈 주식 데일리 브리핑")
st.caption(
    "매일 자동 수집된 국내·미국 뉴스/공시/시세 데이터를 도구 호출 에이전트로 조회합니다. "
    "본 서비스는 정보 제공 목적이며 투자 자문이 아닙니다. 시세는 전일 종가 기준입니다."
)

tab_chat, tab_dash = st.tabs(["💬 Q&A 에이전트", "📊 대시보드"])

# ---------------- chat tab ----------------
with tab_chat:
    if "agent" not in st.session_state:
        st.session_state.agent = Agent()
        st.session_state.messages = []

    st.markdown(
        "예시: `SK하이닉스 주가랑 최근 이슈 알려줘` · `삼성전자 최근 공시 있어?` "
        "· `코스피랑 환율 어떻게 됐어?`"
    )

    for m in st.session_state.messages:
        st.chat_message(m["role"]).markdown(m["content"])

    if question := st.chat_input("질문을 입력하세요"):
        st.chat_message("user").markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("assistant"):
            with st.spinner("도구를 호출하는 중..."):
                try:
                    reply = st.session_state.agent.ask(question)
                except Exception as e:
                    reply = f"오류가 발생했습니다: {e}"
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

# ---------------- dashboard tab ----------------
with tab_dash:
    with db.get_conn() as conn:
        n_articles, = conn.execute("SELECT COUNT(*) FROM articles").fetchone()
        n_disc, = conn.execute("SELECT COUNT(*) FROM disclosures").fetchone()
        latest, = conn.execute("SELECT MAX(collected_at) FROM articles").fetchone()

        daily = pd.read_sql_query(
            "SELECT substr(collected_at,1,10) AS date, market, COUNT(*) AS articles "
            "FROM articles GROUP BY date, market ORDER BY date DESC LIMIT 60",
            conn,
        )
        usage = pd.read_sql_query(
            "SELECT substr(created_at,1,10) AS date, SUM(input_tokens+output_tokens) "
            "AS tokens FROM llm_calls GROUP BY date ORDER BY date DESC LIMIT 30",
            conn,
        )
        from src.config import INDICES, WATCHLIST_KR, WATCHLIST_US
        _tickers = list(WATCHLIST_KR) + list(WATCHLIST_US) + list(INDICES)
        _ph = ",".join("?" * len(_tickers))
        prices = pd.read_sql_query(
            "SELECT p.market, p.name, p.date, p.close FROM prices p "
            "JOIN (SELECT ticker, MAX(date) d FROM prices GROUP BY ticker) m "
            "ON p.ticker = m.ticker AND p.date = m.d "
            f"WHERE p.ticker IN ({_ph}) ORDER BY p.market, p.name",
            conn, params=_tickers,
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("누적 기사", f"{n_articles:,}")
    c2.metric("누적 공시", f"{n_disc:,}")
    c3.metric("마지막 수집(UTC)", (latest or "")[:16])

    st.subheader("일별 수집 기사 수")
    if not daily.empty:
        pivot = daily.pivot_table(index="date", columns="market",
                                  values="articles", fill_value=0)
        st.bar_chart(pivot)

    st.subheader("일별 LLM 토큰 사용량")
    if not usage.empty:
        st.bar_chart(usage.set_index("date"))

    st.subheader("관심종목 최신 종가")
    for market, label in (("KR", "국내"), ("US", "미국"), ("INDEX", "지수·환율")):
        part = prices[prices["market"] == market][["name", "date", "close"]]
        if not part.empty:
            st.markdown(f"**{label}**")
            st.dataframe(part, hide_index=True, use_container_width=True)
