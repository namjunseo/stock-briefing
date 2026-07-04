"""DART disclosure collector (KR)."""
from datetime import datetime, timedelta

import requests

from src.config import DART_API_KEY

LIST_URL = "https://opendart.fss.or.kr/api/list.json"


def collect_dart(days: int = 2) -> list[dict]:
    """Fetch disclosures from the last `days` days (covers weekends/holidays).

    DART status codes: 000=ok, 013=no data (normal on holidays) — both are fine.
    """
    if not DART_API_KEY:
        print("[dart] FAILED: DART_API_KEY not set")
        return []

    bgn_de = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    rows: list[dict] = []
    page = 1
    while True:
        try:
            r = requests.get(
                LIST_URL,
                params={
                    "crtfc_key": DART_API_KEY,
                    "bgn_de": bgn_de,
                    "page_no": page,
                    "page_count": 100,
                },
                timeout=10,
            )
            data = r.json()
        except Exception as exc:
            print(f"[dart] FAILED on page {page}: {exc}")
            break

        if data["status"] == "013":  # no data (weekend/holiday) — not an error
            break
        if data["status"] != "000":
            print(f"[dart] API error: {data}")
            break

        for d in data["list"]:
            rows.append({
                "market": "KR",
                "corp_name": d["corp_name"],
                "title": d["report_nm"].strip(),
                "rcept_no": d["rcept_no"],
                "disclosed_at": f"{d['rcept_dt'][:4]}-{d['rcept_dt'][4:6]}-{d['rcept_dt'][6:]}",
            })

        if page >= int(data.get("total_page", 1)):
            break
        page += 1

    print(f"[dart] {len(rows)} disclosures since {bgn_de}")
    return rows
