"""A tiny dependency-free RAG practice script.

It demonstrates:
- chunk indexing
- BM25 retrieval
- simple reranking
- evidence-grounded answer templating
- retrieval metric calculation

Run from the repository root:
    python rag_learning/practice/toy_rag.py
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    text: str
    source: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


DOCUMENTS = [
    Chunk(
        id="rag-001",
        title="RAG definition",
        source="learning-notes/rag.md",
        text=(
            "Retrieval augmented generation combines an external retriever with a "
            "generator. The retriever selects evidence from a knowledge base, and "
            "the generator answers using the retrieved evidence."
        ),
    ),
    Chunk(
        id="rag-002",
        title="Hybrid retrieval",
        source="learning-notes/retrieval.md",
        text=(
            "Hybrid retrieval combines sparse methods such as BM25 with dense "
            "embedding search. It is useful because keyword matching handles exact "
            "terms while embeddings handle semantic similarity."
        ),
    ),
    Chunk(
        id="rag-003",
        title="Reranking",
        source="learning-notes/rerank.md",
        text=(
            "Reranking scores retrieved candidates again with a stronger model. "
            "A cross encoder can judge whether a chunk directly supports the user question."
        ),
    ),
    Chunk(
        id="rag-004",
        title="Corrective RAG",
        source="learning-notes/crag.md",
        text=(
            "Corrective RAG grades retrieved evidence. If evidence is weak, the system "
            "rewrites the query, searches again, or refuses to answer until stronger "
            "support is found."
        ),
    ),
    Chunk(
        id="rag-005",
        title="GraphRAG",
        source="learning-notes/graphrag.md",
        text=(
            "GraphRAG extracts entities and relationships from documents. It can answer "
            "global or relationship-heavy questions by searching graph neighborhoods "
            "and community summaries."
        ),
    ),
]


EVAL_SET = [
    {
        "question": "Why is hybrid retrieval useful in RAG?",
        "relevant": {"rag-002"},
    },
    {
        "question": "What should a corrective RAG system do when evidence is weak?",
        "relevant": {"rag-004"},
    },
    {
        "question": "Which RAG method uses entities, relationships, and communities?",
        "relevant": {"rag-005"},
    },
]


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.term_freqs = [Counter(tokenize(chunk.title + " " + chunk.text)) for chunk in chunks]
        self.doc_lengths = [sum(freqs.values()) for freqs in self.term_freqs]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        self.doc_freqs = self._doc_freqs()

    def _doc_freqs(self) -> Counter[str]:
        freqs: Counter[str] = Counter()
        for term_freq in self.term_freqs:
            freqs.update(term_freq.keys())
        return freqs

    def search(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        query_terms = tokenize(query)
        scored = []
        for idx, chunk in enumerate(self.chunks):
            score = self._score(query_terms, idx)
            if score > 0:
                scored.append(RetrievedChunk(chunk=chunk, score=score))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:k]

    def _score(self, query_terms: list[str], doc_idx: int) -> float:
        score = 0.0
        term_freq = self.term_freqs[doc_idx]
        doc_length = self.doc_lengths[doc_idx]
        total_docs = len(self.chunks)

        for term in query_terms:
            if term not in term_freq:
                continue
            df = self.doc_freqs[term]
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            tf = term_freq[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            score += idf * numerator / denominator
        return score


def rerank(question: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """A tiny lexical reranker.

    Production systems usually use a cross-encoder, a smaller LLM, or a learned ranker.
    This function is intentionally simple so the ranking mechanics are visible.
    """

    question_terms = set(tokenize(question))
    reranked = []
    for item in candidates:
        title_terms = set(tokenize(item.chunk.title))
        text_terms = set(tokenize(item.chunk.text))
        direct_overlap = len(question_terms & text_terms)
        title_overlap = len(question_terms & title_terms)
        adjusted_score = item.score + 0.8 * title_overlap + 0.2 * direct_overlap
        reranked.append(RetrievedChunk(chunk=item.chunk, score=adjusted_score))
    return sorted(reranked, key=lambda item: item.score, reverse=True)


def answer(question: str, evidence: list[RetrievedChunk]) -> str:
    if not evidence:
        return "I do not have enough evidence to answer."

    top = evidence[0].chunk
    return (
        f"Question: {question}\n"
        f"Answer: Based on {top.id}, {top.text}\n"
        f"Citation: {top.source}#{top.id}"
    )


def recall_at_k(results: list[RetrievedChunk], relevant_ids: set[str], k: int) -> float:
    found = {item.chunk.id for item in results[:k]}
    return len(found & relevant_ids) / len(relevant_ids)


def mrr(results: list[RetrievedChunk], relevant_ids: set[str]) -> float:
    for rank, item in enumerate(results, start=1):
        if item.chunk.id in relevant_ids:
            return 1 / rank
    return 0.0


def run_demo() -> None:
    index = BM25Index(DOCUMENTS)
    question = "How does Corrective RAG handle weak retrieval evidence?"
    initial = index.search(question, k=4)
    final = rerank(question, initial)

    print("Retrieved evidence:")
    for item in final:
        print(f"- {item.chunk.id}: score={item.score:.3f} title={item.chunk.title}")

    print()
    print(answer(question, final[:2]))


def run_eval() -> None:
    index = BM25Index(DOCUMENTS)
    recalls = []
    reciprocal_ranks = []

    print("\nEvaluation:")
    for case in EVAL_SET:
        results = rerank(case["question"], index.search(case["question"], k=4))
        recall = recall_at_k(results, case["relevant"], k=3)
        rank_score = mrr(results, case["relevant"])
        recalls.append(recall)
        reciprocal_ranks.append(rank_score)
        ranked_ids = [item.chunk.id for item in results]
        print(
            f"- q={case['question']!r} top={ranked_ids} "
            f"recall@3={recall:.2f} mrr={rank_score:.2f}"
        )

    print(f"Average recall@3={sum(recalls) / len(recalls):.2f}")
    print(f"MRR={sum(reciprocal_ranks) / len(reciprocal_ranks):.2f}")


if __name__ == "__main__":
    run_demo()
    run_eval()

