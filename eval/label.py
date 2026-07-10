"""Interactive golden-set labeling for retrieval evaluation.

For each question you type, the tool shows top-15 search results.
Enter the numbers of articles that truly answer the question.

Usage:
    python -m eval.label

Output: eval/golden.jsonl  (one {"question", "relevant_ids"} per line)
"""
import json
import os
from datetime import datetime, timezone

from src.embed import embed_texts
from src.rag.store import search

GOLDEN_PATH = os.path.join("eval", "golden.jsonl")
SHOW_K = 15


def load_existing() -> set[str]:
    if not os.path.exists(GOLDEN_PATH):
        return set()
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return {json.loads(line)["question"] for line in f if line.strip()}


def main() -> None:
    os.makedirs("eval", exist_ok=True)
    done = load_existing()
    print(f"골든셋에 {len(done)}개 질문이 이미 있음")
    print("질문 입력 → 후보 중 정답 번호 선택 (쉼표 구분). 종료: 빈 질문 + Enter\n")

    while True:
        try:
            question = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        if question in done:
            print("  이미 라벨링된 질문입니다. 건너뜀.")
            continue

        q_vec = embed_texts([question])[0]
        hits = search(q_vec, top_k=SHOW_K)
        if not hits:
            print("  검색 결과 없음")
            continue
        for i, h in enumerate(hits, 1):
            print(f"  [{i:2d}] ({h['date']}, {h['market']}) {h['title'][:70]}")

        raw = input("정답 번호 (예: 1,3,5 / 정답 없음: 0 / 건너뛰기: s): ").strip()
        if raw.lower() == "s":
            continue
        try:
            picks = [int(x) for x in raw.split(",")] if raw != "0" else []
        except ValueError:
            print("  잘못된 입력. 건너뜀.")
            continue
        if any(p < 0 or p > len(hits) for p in picks):
            print("  범위를 벗어난 번호. 건너뜀.")
            continue

        relevant_ids = [hits[p - 1]["id"] for p in picks]
        record = {
            "question": question,
            "relevant_ids": relevant_ids,
            "labeled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with open(GOLDEN_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        done.add(question)
        print(f"  저장됨 (정답 {len(relevant_ids)}건). 누적 {len(done)}개 질문\n")


if __name__ == "__main__":
    main()
