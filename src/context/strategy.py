"""Context shaping strategies for the diagnostic harness."""

from __future__ import annotations

from tools.memory import IncidentHit
from tools.logs import LogHit
from tools.metrics import MetricPoint
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

    def summarize_logs(self, hits: list[LogHit]) -> str:
        if not hits:
            return "未检索到相关日志。"
        lines = []
        for hit in hits:
            lines.append(
                f"{hit.timestamp} {hit.service} {hit.level} "
                f"(score={hit.score:.2f}, trace={hit.trace_id}): {hit.message}"
            )
        return " | ".join(lines)

    def summarize_metrics(self, points: list[MetricPoint]) -> str:
        if not points:
            return "未检索到相关指标。"
        lines = []
        for point in points:
            lines.append(
                f"{point.service}.{point.metric}={point.value:g}{point.unit} "
                f"(baseline={point.baseline:g}{point.unit}, window={point.window}, "
                f"score={point.score:.2f})"
            )
        return " | ".join(lines)

    def build_observation_query(self, user_request: str, impact_summary: str) -> str:
        return f"{user_request}\n{impact_summary}"

    def build_memory_query(
        self,
        user_request: str,
        impact_summary: str,
        log_summary: str = "",
        metrics_summary: str = "",
    ) -> str:
        return f"{user_request}\n{impact_summary}"
