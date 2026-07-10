"""Retrieval evaluation: compare vector / bm25 / hybrid on the golden set.

Usage:
    python -m eval.run_eval
"""
import json
import os

from src.embed import embed_texts
from src.rag.fusion import rrf_fuse
from src.rag.lexical import LexicalIndex
from src.rag.store import search

GOLDEN_PATH = os.path.join("eval", "golden.jsonl")
KS = (3, 5, 10)
MAX_K = max(KS)
CANDIDATE_K = 20  # how deep each retriever goes before fusion


def load_golden() -> list[dict]:
    with open(GOLDEN_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def metrics(retrieved_per_q: list[list[int]], golden: list[dict]) -> dict:
    recalls = {k: [] for k in KS}
    rr = []
    for retrieved, g in zip(retrieved_per_q, golden):
        relevant = set(g["relevant_ids"])
        for k in KS:
            recalls[k].append(len(relevant & set(retrieved[:k])) / len(relevant))
        rank = next((i + 1 for i, rid in enumerate(retrieved) if rid in relevant), None)
        rr.append(1.0 / rank if rank else 0.0)
    return {
        **{f"recall@{k}": sum(v) / len(v) for k, v in recalls.items()},
        "mrr": sum(rr) / len(rr),
    }


def main() -> None:
    golden = [g for g in load_golden() if g["relevant_ids"]]
    if not golden:
        raise SystemExit("골든셋에 정답이 있는 질문이 없습니다.")

    questions = [g["question"] for g in golden]
    vectors = embed_texts(questions)
    lex = LexicalIndex()

    vector_lists, bm25_lists, hybrid_lists = [], [], []
    for q, v in zip(questions, vectors):
        vec_ids = [h["id"] for h in search(v, top_k=CANDIDATE_K)]
        bm_ids = lex.rank(q, top_k=CANDIDATE_K)
        vector_lists.append(vec_ids[:MAX_K])
        bm25_lists.append(bm_ids[:MAX_K])
        hybrid_lists.append(rrf_fuse([vec_ids, bm_ids], top_k=MAX_K))

    results = {
        "vector": metrics(vector_lists, golden),
        "bm25": metrics(bm25_lists, golden),
        "hybrid": metrics(hybrid_lists, golden),
    }

    print(f"\n=== Retrieval eval (n={len(golden)} questions) ===")
    header = "| method | " + " | ".join(f"recall@{k}" for k in KS) + " | MRR |"
    print(header)
    print("|" + "---|" * (len(KS) + 2))
    for name, r in results.items():
        cells = " | ".join(f"{r[f'recall@{k}']:.3f}" for k in KS)
        print(f"| {name} | {cells} | {r['mrr']:.3f} |")


if __name__ == "__main__":
    main()
