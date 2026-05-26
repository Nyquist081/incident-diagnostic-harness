"""Historical incident retrieval tool backed by Sprint 2 mock data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol

from tools.text_match import SimpleBM25


@dataclass(frozen=True)
class IncidentHit:
    incident_id: str
    service: str
    symptom: str
    root_cause: str
    resolution: str
    tags: list[str]
    score: float


class IncidentMemoryProvider(Protocol):
    def search(self, query: str, *, top_k: int = 3) -> list[IncidentHit]:
        """Return ranked historical incidents for a query."""


class BM25MemoryProvider:
    def __init__(self, incidents: list[dict[str, Any]]) -> None:
        self.incidents = incidents
        corpus = [
            " ".join(
                [
                    item["service"],
                    item["symptom"],
                    item["root_cause"],
                    item["resolution"],
                    " ".join(item.get("tags", [])),
                ]
            )
            for item in incidents
        ]
        self.index = SimpleBM25(corpus)

    def search(self, query: str, *, top_k: int = 3) -> list[IncidentHit]:
        ranked = self.index.rank(query, top_k=top_k)
        return [self._to_hit(self.incidents[item.index], item.score) for item in ranked]

    def _to_hit(self, incident: dict[str, Any], score: float) -> IncidentHit:
        return IncidentHit(
            incident_id=incident["id"],
            service=incident["service"],
            symptom=incident["symptom"],
            root_cause=incident["root_cause"],
            resolution=incident["resolution"],
            tags=list(incident.get("tags", [])),
            score=score,
        )


class FastEmbedMemoryProvider:
    """Optional local vector provider backed by FastEmbed.

    This provider is intentionally lazy-imported so the harness can run without
    downloading embedding dependencies until vector retrieval is enabled.
    """

    def __init__(self, incidents: list[dict[str, Any]], *, model_name: str) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "FastEmbed memory provider requires `uv add fastembed` before use."
            ) from exc
        self.incidents = incidents
        self.model = TextEmbedding(model_name=model_name)
        self.corpus = [
            " ".join(
                [
                    item["service"],
                    item["symptom"],
                    item["root_cause"],
                    item["resolution"],
                    " ".join(item.get("tags", [])),
                ]
            )
            for item in incidents
        ]
        self.vectors = list(self.model.embed(self.corpus))

    def search(self, query: str, *, top_k: int = 3) -> list[IncidentHit]:
        query_vector = next(self.model.embed([query]))
        scored = [
            (index, _cosine_similarity(query_vector, vector))
            for index, vector in enumerate(self.vectors)
        ]
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]
        return [self._to_hit(self.incidents[index], score) for index, score in ranked]

    def _to_hit(self, incident: dict[str, Any], score: float) -> IncidentHit:
        return IncidentHit(
            incident_id=incident["id"],
            service=incident["service"],
            symptom=incident["symptom"],
            root_cause=incident["root_cause"],
            resolution=incident["resolution"],
            tags=list(incident.get("tags", [])),
            score=score,
        )


def _cosine_similarity(left: Any, right: Any) -> float:
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = sum(float(a) * float(a) for a in left) ** 0.5
    right_norm = sum(float(b) * float(b) for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def build_memory_provider(
    incidents: list[dict[str, Any]],
    *,
    provider: str,
    embedding_model: str,
) -> IncidentMemoryProvider:
    if provider == "fastembed":
        return FastEmbedMemoryProvider(incidents, model_name=embedding_model)
    if provider == "bm25":
        return BM25MemoryProvider(incidents)
    raise ValueError(f"Unsupported memory provider: {provider}")


MemoryTool = BM25MemoryProvider
