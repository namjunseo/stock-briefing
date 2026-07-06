"""Project configuration: env vars, watchlists, feed URLs."""
import os

from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.environ.get("DART_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DB_PATH = os.environ.get("DB_PATH", "stock_briefing.db")

GEMINI_MODEL = "gemini-3.1-flash-lite"

EDGAR_USER_AGENT = "stock-briefing namjunseo051219@gmail.com"
# EDGAR filing types worth surfacing in a briefing
EDGAR_FORMS = {"8-K", "10-Q", "10-K"}

# --- News sources ---
RSS_FEEDS = [
    {"market": "KR", "source": "hankyung_finance", "url": "https://www.hankyung.com/feed/finance"},
    {"market": "KR", "source": "hankyung_economy", "url": "https://www.hankyung.com/feed/economy"},
    {"market": "US", "source": "marketwatch_top", "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"market": "US", "source": "yahoo_finance", "url": "https://finance.yahoo.com/news/rssindex"},
]

# Some feed servers reject default library User-Agents
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# --- Watchlist ---
# KR name must exactly match the DART corp_name for disclosure filtering.
# yfinance format: KOSPI=.KS, KOSDAQ=.KQ
WATCHLIST_KR = {
    "000660.KS": "SK하이닉스",
    "009150.KS": "삼성전기",
    "402340.KS": "SK스퀘어",
    "005380.KS": "현대자동차",
    "005930.KS": "삼성전자",
    "035420.KS": "NAVER",
    "066570.KS": "LG전자",
}

WATCHLIST_US = {
    "SNDK": "샌디스크",
    "ASML": "ASML",
    "MU": "마이크론",
    "META": "메타",
    "AMD": "AMD",
    "TSM": "TSMC",
    "TSLA": "테슬라",
    "MSFT": "마이크로소프트",
    "AVGO": "브로드컴",
    "GOOGL": "알파벳",
    "AAPL": "애플",
    "MRVL": "마벨",
    "AMZN": "아마존",
    "NVDA": "엔비디아",
    "PLTR": "팔란티어",
    "INTC": "인텔",
    "SPCX": "스페이스X",
}

INDICES = {
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
    "^GSPC": "S&P500",
    "^IXIC": "NASDAQ",
    "USDKRW=X": "USD/KRW",
}
