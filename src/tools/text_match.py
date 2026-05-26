"""Deterministic text matching helpers for local retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\-]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


@dataclass(frozen=True)
class RankedDocument:
    index: int
    score: float


class SimpleBM25:
    """A compact BM25 implementation for local incident retrieval."""

    def __init__(self, documents: list[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.tokenized = [tokenize(document) for document in documents]
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.tokenized:
            self.doc_freq.update(set(tokens))
        self.avg_doc_len = (
            sum(len(tokens) for tokens in self.tokenized) / len(self.tokenized)
            if self.tokenized
            else 0.0
        )

    def rank(self, query: str, *, top_k: int = 3) -> list[RankedDocument]:
        query_terms = tokenize(query)
        ranked: list[RankedDocument] = []
        for index, tokens in enumerate(self.tokenized):
            score = self._score(tokens, query_terms)
            if score > 0:
                ranked.append(RankedDocument(index=index, score=score))
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]

    def _score(self, tokens: list[str], query_terms: list[str]) -> float:
        if not tokens or not query_terms:
            return 0.0
        term_counts = Counter(tokens)
        doc_len = len(tokens)
        total_docs = len(self.tokenized)
        score = 0.0
        for term in query_terms:
            freq = term_counts.get(term, 0)
            if freq == 0:
                continue
            doc_freq = self.doc_freq.get(term, 0)
            idf = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * (freq * (self.k1 + 1) / denominator)
        return score
