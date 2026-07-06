"""Interactive RAG Q&A over collected news.

Usage:
    python chat.py              # search all history
    python chat.py --days 2     # restrict to last 2 days
"""
import sys

from src.rag.qa import answer

def main() -> None:
    days = None
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])

    print("질문을 입력하세요 (종료: 빈 줄 + Enter)")
    while True:
        try:
            question = input("\nQ> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break

        result = answer(question, days=days)
        print(f"\n{result['answer']}\n")
        for i, s in enumerate(result["sources"], 1):
            print(f"  [{i}] ({s['date']}, score {s['score']:.2f}) {s['title'][:60]}")
            print(f"      {s['url']}")


if __name__ == "__main__":
    main()
