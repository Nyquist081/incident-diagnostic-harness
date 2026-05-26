"""Context shaping strategies for the diagnostic harness."""

from __future__ import annotations

from tools.memory import IncidentHit
from tools.topology import TopologyImpact


class DiagnosticContextStrategy:
    """Convert raw tool results into compact state fields."""

    def summarize_topology(self, impact: TopologyImpact) -> str:
        upstream = ", ".join(impact.upstream) if impact.upstream else "无直接上游"
        downstream = ", ".join(impact.downstream) if impact.downstream else "无直接下游"
        return (
            f"服务 {impact.service} 匹配输入别名 {impact.matched_alias}；"
            f"负责人 {impact.owner}；上游: {upstream}；下游: {downstream}。"
        )

    def summarize_memory(self, hits: list[IncidentHit]) -> str:
        if not hits:
            return "未检索到相似历史故障。"
        lines = []
        for hit in hits:
            lines.append(
                f"{hit.incident_id}({hit.service}, score={hit.score:.2f}): "
                f"{hit.symptom}；根因: {hit.root_cause}；处置: {hit.resolution}"
            )
        return " | ".join(lines)

    def build_memory_query(self, user_request: str, impact_summary: str) -> str:
        return f"{user_request}\n{impact_summary}"
