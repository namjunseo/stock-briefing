"""RAG Q&A: retrieve relevant articles, answer with sources."""
import time
from datetime import datetime, timedelta, timezone

from google import genai

from src import db
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.embed import embed_texts
from src.rag.store import search

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


PROMPT_TEMPLATE = """너는 수집된 뉴스 기사 제목을 근거로 질문에 답하는 도우미다.

[검색된 기사]
{context}

[질문]
{question}

규칙:
- 위 기사들에 있는 내용만으로 답하라. 기사에 없는 사실, 수치, 전망을 추가하지 마라.
- 답에 사용한 기사는 [1], [2] 형식으로 번호를 인용하라.
- 기사들로 답할 수 없는 질문이면 "수집된 기사에서 관련 내용을 찾지 못했습니다"라고 답하라.
- 매수/매도 등 투자 판단을 요청받으면: 투자 자문은 제공하지 않는다고 밝히고, 관련 정보만 정리하라.

답변:"""


def answer(question: str, top_k: int = 8, days: int | None = None) -> dict:
    """Returns {"answer": str, "sources": [ ... ]}."""
    since = None
    if days is not None:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(
            timespec="seconds")

    q_vec = embed_texts([question])[0]
    hits = search(q_vec, top_k=top_k, since=since)
    if not hits:
        return {"answer": "수집된 기사가 없습니다. collect.py와 index.py를 먼저 실행하세요.",
                "sources": []}

    context = "\n".join(
        f"[{i+1}] ({h['date']}, {h['source']}) {h['title']}"
        for i, h in enumerate(hits)
    )
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    client = _get_client()
    t0 = time.monotonic()
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    latency_ms = int((time.monotonic() - t0) * 1000)

    usage = resp.usage_metadata
    db.log_llm_call(
        model=GEMINI_MODEL,
        purpose="rag_qa",
        input_tokens=usage.prompt_token_count or 0,
        output_tokens=usage.candidates_token_count or 0,
        latency_ms=latency_ms,
    )
    return {"answer": resp.text.strip(), "sources": hits}
