"""Log search provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from tools.text_match import SimpleBM25


@dataclass(frozen=True)
class LogHit:
    service: str
    timestamp: str
    level: str
    message: str
    trace_id: str
    score: float


class LogSearchProvider(Protocol):
    def search(self, query: str, *, top_k: int = 5) -> list[LogHit]:
        """Return ranked log events for a query."""


class MockLogProvider:
    def __init__(self, logs: list[dict[str, Any]]) -> None:
        self.logs = logs
        corpus = [
            " ".join([item["service"], item["level"], item["message"], item["trace_id"]])
            for item in logs
        ]
        self.index = SimpleBM25(corpus)

    def search(self, query: str, *, top_k: int = 5) -> list[LogHit]:
        ranked = self.index.rank(query, top_k=top_k)
        return [self._to_hit(self.logs[item.index], item.score) for item in ranked]

    def _to_hit(self, item: dict[str, Any], score: float) -> LogHit:
        return LogHit(
            service=item["service"],
            timestamp=item["timestamp"],
            level=item["level"],
            message=item["message"],
            trace_id=item["trace_id"],
            score=score,
        )
