"""Topology retrieval tool backed by Sprint 2 mock data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.text_match import tokenize


@dataclass(frozen=True)
class TopologyImpact:
    service: str
    upstream: list[str]
    downstream: list[str]
    owner: str
    matched_alias: str


class TopologyTool:
    def __init__(self, topology_data: dict[str, Any]) -> None:
        self.services = topology_data["services"]

    def lookup(self, query: str) -> TopologyImpact:
        service = self._match_service(query)
        return TopologyImpact(
            service=service["name"],
            upstream=list(service["upstream"]),
            downstream=list(service["downstream"]),
            owner=service["owner"],
            matched_alias=service["matched_alias"],
        )

    def _match_service(self, query: str) -> dict[str, Any]:
        query_lower = query.lower()
        query_tokens = set(tokenize(query))
        best: tuple[int, dict[str, Any]] | None = None
        for service in self.services:
            aliases = [service["name"], *service.get("aliases", [])]
            score = 0
            matched_alias = service["name"]
            for alias in aliases:
                alias_lower = alias.lower()
                alias_tokens = set(tokenize(alias))
                if alias_lower in query_lower:
                    score = max(score, 100 + len(alias_lower))
                    matched_alias = alias
                overlap = len(query_tokens & alias_tokens)
                if overlap > score:
                    score = overlap
                    matched_alias = alias
            candidate = {**service, "matched_alias": matched_alias}
            if best is None or score > best[0]:
                best = (score, candidate)
        if best is None:
            raise ValueError("No services configured in topology data.")
        return best[1]
