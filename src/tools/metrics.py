"""Metrics provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from tools.text_match import SimpleBM25


@dataclass(frozen=True)
class MetricPoint:
    service: str
    metric: str
    window: str
    value: float
    baseline: float
    unit: str
    score: float


class MetricsProvider(Protocol):
    def search(self, query: str, *, top_k: int = 5) -> list[MetricPoint]:
        """Return ranked metric points for a query."""


class MockMetricsProvider:
    def __init__(self, metrics: list[dict[str, Any]]) -> None:
        self.metrics = metrics
        corpus = [
            " ".join([item["service"], item["metric"], item["window"], item["unit"]])
            for item in metrics
        ]
        self.index = SimpleBM25(corpus)

    def search(self, query: str, *, top_k: int = 5) -> list[MetricPoint]:
        ranked = self.index.rank(query, top_k=top_k)
        return [self._to_point(self.metrics[item.index], item.score) for item in ranked]

    def _to_point(self, item: dict[str, Any], score: float) -> MetricPoint:
        return MetricPoint(
            service=item["service"],
            metric=item["metric"],
            window=item["window"],
            value=float(item["value"]),
            baseline=float(item["baseline"]),
            unit=item["unit"],
            score=score,
        )
