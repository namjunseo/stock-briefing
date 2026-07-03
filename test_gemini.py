"""Smoke test: check Gemini API key works and find a usable free-tier model.

Usage:
    python test_gemini.py
"""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 1) List models available to this key (flash models only, to keep output short)
print("--- Available flash models ---")
flash_models = []
for m in client.models.list():
    if "flash" in m.name.lower():
        flash_models.append(m.name)
        print(m.name)

# 2) Try candidates in order until one responds
CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
]
# also try whatever the API listed, as a fallback
CANDIDATES += [m.replace("models/", "") for m in flash_models]

print("\n--- Generation test ---")
for model in dict.fromkeys(CANDIDATES):  # dedupe, keep order
    try:
        resp = client.models.generate_content(
            model=model,
            contents="다음 문장을 한 줄로 요약해줘: 삼성전자가 2분기 잠정 실적을 발표했다.",
        )
        usage = resp.usage_metadata
        print(f"[OK] model={model}")
        print(f"     response: {resp.text.strip()[:80]}")
        print(f"     tokens: in={usage.prompt_token_count}, out={usage.candidates_token_count}")
        break
    except Exception as e:
        print(f"[SKIP] {model}: {str(e)[:100]}")
else:
    print("[FAIL] no model worked — paste this output to Claude")
