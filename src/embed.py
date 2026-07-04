"""Gemini embedding wrapper."""
import time

from google import genai

from src.config import GEMINI_API_KEY

EMBED_MODEL = "gemini-embedding-001"
BATCH_SIZE = 100  # API accepts batched contents; keep requests small

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, batching requests. Returns one vector per text."""
    client = _get_client()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        resp = client.models.embed_content(model=EMBED_MODEL, contents=batch)
        vectors.extend(e.values for e in resp.embeddings)
        if i + BATCH_SIZE < len(texts):
            time.sleep(1)  # be polite to free-tier rate limits
    return vectors
