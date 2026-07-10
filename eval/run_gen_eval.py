"""Generation evaluation with LLM-as-judge.

For every golden question (including no-answer ones), generate an answer
via the RAG pipeline, then have a judge model score it:
  - faithfulness (1-5): every claim traceable to the retrieved sources
  - hallucination (bool): contains facts not present in sources
  - admits_gap (bool): properly says info was not found (when it wasn't)

Usage:
    python -m eval.run_gen_eval
"""
import json
import re
import time

from google import genai
from google.genai import errors

from src import db
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.rag.qa import answer

GOLDEN_PATH = "eval/golden.jsonl"
SLEEP_BETWEEN_QUESTIONS = 8  # 2 generate calls per question, ~15 RPM free tier

JUDGE_PROMPT = """너는 RAG 시스템의 답변을 채점하는 엄격한 심판이다.

[검색된 출처 (답변이 근거로 삼을 수 있는 전부)]
{context}

[질문]
{question}

[시스템의 답변]
{answer}

다음 JSON 형식으로만 답하라. 다른 텍스트 금지.
{{"faithfulness": <1-5, 답변의 모든 주장이 출처에서 확인되면 5, 절반 이하면 2 이하>,
"hallucination": <true/false, 출처에 없는 사실·수치·전망이 하나라도 있으면 true>,
"admits_gap": <true/false, 출처로 답할 수 없는 부분을 "찾지 못했다"고 인정했으면 true>,
"comment": "<한 줄 근거>"}}"""


_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def parse_judge(text: str) -> dict | None:
    """Parse judge output, tolerating code fences and stray text."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(d.get("faithfulness"), (int, float)):
        return None
    return {
        "faithfulness": max(1, min(5, int(d["faithfulness"]))),
        "hallucination": bool(d.get("hallucination", False)),
        "admits_gap": bool(d.get("admits_gap", False)),
        "comment": str(d.get("comment", ""))[:200],
    }


def judge(question: str, sources: list[dict], answer_text: str) -> dict | None:
    context = "\n".join(
        f"[{i+1}] ({s['date']}, {s['source']}) {s['title']}"
        for i, s in enumerate(sources)
    )
    prompt = JUDGE_PROMPT.format(context=context, question=question, answer=answer_text)

    client = _get_client()
    for attempt in range(2):
        try:
            t0 = time.monotonic()
            resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
            latency_ms = int((time.monotonic() - t0) * 1000)
            usage = resp.usage_metadata
            db.log_llm_call(GEMINI_MODEL, "judge",
                            usage.prompt_token_count or 0,
                            usage.candidates_token_count or 0, latency_ms)
            return parse_judge(resp.text)
        except errors.ClientError as e:
            if (getattr(e, "code", None) == 429 or "429" in str(e)) and attempt == 0:
                print("  [judge] rate limited; waiting 30s")
                time.sleep(30)
            else:
                raise
    return None


def main() -> None:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        golden = [json.loads(line) for line in f if line.strip()]

    results = []
    for i, g in enumerate(golden, 1):
        q = g["question"]
        print(f"[{i}/{len(golden)}] {q[:40]}")
        try:
            r = answer(q)
            verdict = judge(q, r["sources"], r["answer"])
        except Exception as e:
            print(f"  FAILED: {e}")
            verdict = None
        if verdict:
            verdict["question"] = q
            verdict["has_answer"] = bool(g["relevant_ids"])
            results.append(verdict)
        time.sleep(SLEEP_BETWEEN_QUESTIONS)

    if not results:
        raise SystemExit("no results")

    answered = [r for r in results if r["has_answer"]]
    no_answer = [r for r in results if not r["has_answer"]]

    print(f"\n=== Generation eval (judged: {len(results)}) ===")
    if answered:
        avg_f = sum(r["faithfulness"] for r in answered) / len(answered)
        hall = sum(r["hallucination"] for r in answered) / len(answered)
        print(f"[정답 있는 질문 n={len(answered)}]")
        print(f"  faithfulness 평균 = {avg_f:.2f} / 5")
        print(f"  hallucination 비율 = {hall:.1%}")
    if no_answer:
        ok = sum(1 for r in no_answer if r["admits_gap"] and not r["hallucination"])
        print(f"[정답 없는 질문 n={len(no_answer)}]")
        print(f"  올바른 '모름' 응답 비율 = {ok}/{len(no_answer)} ({ok/len(no_answer):.1%})")

    bad = [r for r in results if r["hallucination"] or r["faithfulness"] <= 2]
    if bad:
        print(f"\n--- 검토 필요 ({len(bad)}건) ---")
        for r in bad:
            print(f"  Q: {r['question'][:40]}")
            print(f"     f={r['faithfulness']}, hall={r['hallucination']}: {r['comment']}")

    with open("eval/gen_eval_results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("\n상세 결과 저장: eval/gen_eval_results.jsonl")


if __name__ == "__main__":
    main()
