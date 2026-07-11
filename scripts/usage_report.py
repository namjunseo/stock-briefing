"""LLM usage report from the llm_calls log.

Shows calls/tokens/latency by purpose and by day, plus estimated cost
at paid rates (we run on the free tier — this is the "환산 비용").

Usage:
    python -m scripts.usage_report
"""
from src import db

# Paid-tier rates in USD per 1M tokens. We use the free tier, so this is
# a what-if figure. TODO: verify against current pricing before quoting.
RATE_IN_PER_M = 0.10
RATE_OUT_PER_M = 0.40
USD_KRW = 1400


def fetch(sql: str) -> list:
    with db.get_conn() as conn:
        return conn.execute(sql).fetchall()


def main() -> None:
    total = fetch(
        "SELECT COUNT(*) n, SUM(input_tokens) ti, SUM(output_tokens) to_, "
        "AVG(latency_ms) lat FROM llm_calls")[0]
    if not total["n"]:
        raise SystemExit("no llm_calls logged yet")

    cost_usd = (total["ti"] * RATE_IN_PER_M + total["to_"] * RATE_OUT_PER_M) / 1e6
    print("=== 전체 누적 ===")
    print(f"호출 {total['n']:,}회 | tokens in/out = {total['ti']:,}/{total['to_']:,} "
          f"| 평균 지연 {total['lat']:.0f}ms")
    print(f"유료 단가 환산 비용: ${cost_usd:.3f} (약 {cost_usd*USD_KRW:,.0f}원) — 실지출 $0")

    print("\n=== 용도별 ===")
    print(f"{'purpose':<18s} {'calls':>6s} {'tok_in':>10s} {'tok_out':>9s} {'avg_ms':>7s}")
    for r in fetch(
        "SELECT purpose, COUNT(*) n, SUM(input_tokens) ti, SUM(output_tokens) to_, "
        "AVG(latency_ms) lat FROM llm_calls GROUP BY purpose ORDER BY ti DESC"):
        print(f"{r['purpose']:<18s} {r['n']:>6,d} {r['ti']:>10,d} {r['to_']:>9,d} "
              f"{r['lat']:>7.0f}")

    print("\n=== 일별 (최근 14일) ===")
    print(f"{'date':<12s} {'calls':>6s} {'tok_in':>10s} {'tok_out':>9s}")
    for r in fetch(
        "SELECT substr(created_at, 1, 10) d, COUNT(*) n, SUM(input_tokens) ti, "
        "SUM(output_tokens) to_ FROM llm_calls GROUP BY d ORDER BY d DESC LIMIT 14"):
        print(f"{r['d']:<12s} {r['n']:>6,d} {r['ti']:>10,d} {r['to_']:>9,d}")


if __name__ == "__main__":
    main()
