"""Gemini embedding wrapper (free-tier friendly: batching + 429 retry)."""
import time

from google import genai
from google.genai import errors

from src.config import GEMINI_API_KEY

EMBED_MODEL = "gemini-embedding-001"
BATCH_SIZE = 50  # each item counts toward the 100 req/min free-tier quota
PAUSE_S = 35     # keep consecutive batches under the per-minute limit

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _embed_batch(batch: list[str], max_retries: int = 3) -> list[list[float]]:
    client = _get_client()
    for attempt in range(max_retries):
        try:
            resp = client.models.embed_content(model=EMBED_MODEL, contents=batch)
            return [e.values for e in resp.embeddings]
        except errors.ClientError as e:
            if getattr(e, "code", None) == 429 and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                print(f"[embed] rate limited; retrying in {wait}s")
                time.sleep(wait)
            else:
                raise
    return []


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in rate-limit-safe batches."""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_embed_batch(texts[i : i + BATCH_SIZE]))
        if i + BATCH_SIZE < len(texts):
            time.sleep(PAUSE_S)
    return vectors
