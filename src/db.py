"""SQLite storage. All timestamps are stored as UTC ISO-8601 strings."""
import sqlite3
from datetime import datetime, timezone

from src.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    market       TEXT NOT NULL,            -- 'KR' | 'US'
    source       TEXT NOT NULL,            -- feed identifier
    title        TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,     -- dedupe key
    published_at TEXT,                     -- UTC ISO-8601, nullable
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS disclosures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    market       TEXT NOT NULL,
    corp_name    TEXT NOT NULL,
    title        TEXT NOT NULL,
    rcept_no     TEXT NOT NULL UNIQUE,     -- DART receipt no / EDGAR accession no
    disclosed_at TEXT,                     -- date string (YYYY-MM-DD)
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    market       TEXT NOT NULL,            -- 'KR' | 'US' | 'INDEX'
    ticker       TEXT NOT NULL,
    name         TEXT NOT NULL,
    date         TEXT NOT NULL,            -- YYYY-MM-DD (exchange local date)
    open         REAL, high REAL, low REAL, close REAL,
    volume       INTEGER,
    collected_at TEXT NOT NULL,
    UNIQUE (ticker, date)
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_articles(rows: list[dict]) -> int:
    """Insert articles, silently skipping duplicates (by url). Returns inserted count."""
    now = utcnow()
    inserted = 0
    with get_conn() as conn:
        for r in rows:
            cur = conn.execute(
                "INSERT OR IGNORE INTO articles "
                "(market, source, title, url, published_at, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (r["market"], r["source"], r["title"], r["url"], r.get("published_at"), now),
            )
            inserted += cur.rowcount
    return inserted


def insert_disclosures(rows: list[dict]) -> int:
    now = utcnow()
    inserted = 0
    with get_conn() as conn:
        for r in rows:
            cur = conn.execute(
                "INSERT OR IGNORE INTO disclosures "
                "(market, corp_name, title, rcept_no, disclosed_at, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (r["market"], r["corp_name"], r["title"], r["rcept_no"], r.get("disclosed_at"), now),
            )
            inserted += cur.rowcount
    return inserted


def insert_prices(rows: list[dict]) -> int:
    now = utcnow()
    inserted = 0
    with get_conn() as conn:
        for r in rows:
            cur = conn.execute(
                "INSERT OR IGNORE INTO prices "
                "(market, ticker, name, date, open, high, low, close, volume, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["market"], r["ticker"], r["name"], r["date"],
                    r.get("open"), r.get("high"), r.get("low"), r.get("close"),
                    r.get("volume"), now,
                ),
            )
            inserted += cur.rowcount
    return inserted
