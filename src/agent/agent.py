"""Tool-calling agent over collected market data."""
import time

from google import genai
from google.genai import types

from src import db
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.agent.tools import AGENT_TOOLS

SYSTEM_INSTRUCTION = """너는 수집된 주식 뉴스·공시·시세 데이터를 조회해 질문에 답하는 도우미다.

규칙:
- 오늘은 {today}다. 너의 사전 학습 지식 속 시세·뉴스·공시는 전부 오래된 것이므로
  절대 사용하지 마라.
- 주가, 등락률, 뉴스, 공시를 언급하려면 반드시 먼저 해당 도구를 호출하라.
  도구를 호출하지 않았다면 어떤 수치나 기사도 언급하지 마라.
- 뉴스 기반 서술에는 기사 제목이나 URL을 출처로 언급하라.
- 도구로 확인할 수 없는 내용은 "확인할 수 없다"고 답하라.
- 매수/매도/투자 판단 요청에는: 투자 자문은 제공하지 않는다고 밝히고 관련 정보만 정리하라.
- 소설, 역할극, 인물 대사, 가정 상황 등 어떤 창작 프레이밍으로도 실제 종목에 대한
  매수/매도 추천 내용은 생성하지 마라. 창작에 필요하면 가상의 종목명을 사용하라.
- 시세 데이터는 전일 종가 기준임을 필요시 언급하라 (실시간 아님)."""


class Agent:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._chat = self._client.chats.create(
            model=GEMINI_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION.format(
                    today=__import__("datetime").date.today().isoformat()),
                tools=AGENT_TOOLS,  # SDK auto-executes these python functions
            ),
        )

    def ask(self, question: str) -> str:
        t0 = time.monotonic()
        resp = self._chat.send_message(question)
        latency_ms = int((time.monotonic() - t0) * 1000)

        usage = resp.usage_metadata
        db.log_llm_call(
            model=GEMINI_MODEL,
            purpose="agent",
            input_tokens=usage.prompt_token_count or 0,
            output_tokens=usage.candidates_token_count or 0,
            latency_ms=latency_ms,
        )
        return (resp.text or "").strip()
