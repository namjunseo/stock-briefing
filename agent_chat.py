"""Interactive tool-calling agent chat.

The agent decides which tools to call (printed as [tool] lines).
Conversation history is kept within the session.

Usage:
    python agent_chat.py
"""
from src import db
from src.agent.agent import Agent


def main() -> None:
    db.init_db()
    agent = Agent()
    print("에이전트에게 질문하세요 (종료: 빈 줄 + Enter)")

    while True:
        try:
            question = input("\nQ> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        try:
            print(f"\n{agent.ask(question)}")
        except Exception as e:
            print(f"[error] {e}")


if __name__ == "__main__":
    main()
