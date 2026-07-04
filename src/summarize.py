"""Issue summarization via Gemini, with per-call usage logging."""
import time

from google import genai

from src import db
from src.config import GEMINI_API_KEY, GEMINI_MODEL

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


PROMPT_TEMPLATE = """다음은 같은 이슈를 다룬 뉴스 기사 제목들이다.

{titles}

이 이슈를 2문장 이내로 요약하라. 규칙:
- 제목들에 나온 정보만 사용할 것. 새로운 사실, 수치, 전망을 추가하지 말 것.
- 제목들이 서로 다른 여러 사건이면 가장 많이 다뤄진 사건 중심으로 요약할 것.
- 투자 추천이나 매수/매도 의견을 포함하지 말 것.
요약:"""


def summarize_issue(issue: dict, max_titles: int = 10) -> str:
    """Summarize one issue from its article titles. Logs token usage to DB."""
    titles = "\n".join(f"- {a['title']}" for a in issue["articles"][:max_titles])
    prompt = PROMPT_TEMPLATE.format(titles=titles)

    client = _get_client()
    t0 = time.monotonic()
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    latency_ms = int((time.monotonic() - t0) * 1000)

    usage = resp.usage_metadata
    db.log_llm_call(
        model=GEMINI_MODEL,
        purpose="issue_summary",
        input_tokens=usage.prompt_token_count or 0,
        output_tokens=usage.candidates_token_count or 0,
        latency_ms=latency_ms,
    )
    return resp.text.strip().removeprefix("요약:").strip()
