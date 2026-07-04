"""Project configuration: env vars, watchlists, feed URLs."""
import os

from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.environ.get("DART_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DB_PATH = os.environ.get("DB_PATH", "stock_briefing.db")

GEMINI_MODEL = "gemini-3.1-flash-lite"

EDGAR_USER_AGENT = "stock-briefing namjunseo051219@gmail.com"

# --- News sources (KR for now; US feeds added in week 5) ---
RSS_FEEDS = [
    {"market": "KR", "source": "hankyung_finance", "url": "https://www.hankyung.com/feed/finance"},
    {"market": "KR", "source": "hankyung_economy", "url": "https://www.hankyung.com/feed/economy"},
]

# Some feed servers reject default library User-Agents
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# --- Watchlist (start small; expand later) ---
# NOTE: full KOSPI200 listing requires KRX login since 2025-12, so we manage
# a manual watchlist instead. yfinance format: KOSPI=.KS, KOSDAQ=.KQ
WATCHLIST_KR = {
    "005930.KS": "삼성전자",
    "000660.KS": "SK하이닉스",
    "373220.KS": "LG에너지솔루션",
    "207940.KS": "삼성바이오로직스",
    "005380.KS": "현대차",
    "051910.KS": "LG화학",
    "035420.KS": "NAVER",
    "035720.KS": "카카오",
    "005490.KS": "POSCO홀딩스",
    "105560.KS": "KB금융",
}

WATCHLIST_US = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "META": "Meta",
}

INDICES = {
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
    "^GSPC": "S&P500",
    "^IXIC": "NASDAQ",
    "USDKRW=X": "USD/KRW",
}
