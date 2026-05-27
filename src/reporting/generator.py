"""Report generation strategies for the diagnostic harness."""

from __future__ import annotations

from typing import Protocol

from core.contracts import DiagnosticReport
from core.messages import latest_user_request
from core.model_factory import ModelFactory
from core.state import EngineState
from prompts.loader import PROMPTS


class ReportGenerator(Protocol):
    def generate(self, state: EngineState) -> DiagnosticReport:
        """Build a structured diagnostic report from engine state."""


class TemplateReportGenerator:
    """Deterministic report generator used for offline and fallback mode."""

    def generate(self, state: EngineState) -> DiagnosticReport:
        user_request = latest_user_request(state.get("messages", []))
        fix_result = state.get("fix_execution_result") or "未执行"
        likely_root_cause, actions = _scenario_guidance(
            user_request,
            state.get("memory_summary", ""),
        )
        return DiagnosticReport(
            title="微服务故障诊断报告",
            impact=state.get("impact_summary") or "未获取拓扑影响面。",
            likely_root_cause=likely_root_cause,
            evidence=[
                f"用户请求: {user_request}",
                f"日志证据: {state.get('log_summary') or '未检索到日志证据。'}",
                f"指标证据: {state.get('metrics_summary') or '未检索到指标证据。'}",
                f"历史记忆: {state.get('memory_summary') or '未检索到历史记忆。'}",
                f"模拟执行结果: {fix_result}",
                f"人工反馈: {state.get('operator_feedback') or '无'}",
            ],
            recommended_actions=actions,
            confidence="medium",
        )


class LLMReportGenerator:
    """Pydantic-validated LLM report generator with template fallback."""

    def __init__(self, model_factory: ModelFactory) -> None:
        self.model_factory = model_factory
        self.fallback = TemplateReportGenerator()

    def generate(self, state: EngineState) -> DiagnosticReport:
        report, _errors = self.generate_with_errors(state)
        return report

    def generate_with_errors(self, state: EngineState) -> tuple[DiagnosticReport, list[str]]:
        settings = self.model_factory.settings
        if not (settings.has_openai_credentials and settings.enable_llm_report):
            return self.fallback.generate(state), []
        try:
            llm = self.model_factory.report_chat().with_structured_output(
                DiagnosticReport,
                method="json_mode",
            )
            prompt = PROMPTS.pair(
                "report_system_v1.md",
                "report_user_v1.md",
                user_request=latest_user_request(state.get("messages", [])),
                impact_summary=state.get("impact_summary", ""),
                log_summary=state.get("log_summary", ""),
                metrics_summary=state.get("metrics_summary", ""),
                memory_summary=state.get("memory_summary", ""),
                fix_plan=state.get("fix_plan", ""),
                fix_execution_result=state.get("fix_execution_result", ""),
                operator_feedback=state.get("operator_feedback", ""),
            )
            response = llm.invoke(
                [
                    ("system", prompt.system),
                    ("human", prompt.user),
                ]
            )
            if isinstance(response, DiagnosticReport):
                return response, []
            return DiagnosticReport.model_validate(response), []
        except Exception as exc:
            return self.fallback.generate(state), [f"report_model={settings.report_model} failed: {type(exc).__name__}: {exc}"]


def render_report(report: DiagnosticReport) -> str:
    evidence = "\n".join(f"  - {item}" for item in report.evidence) or "  - 无"
    actions = "\n".join(f"  - {item}" for item in report.recommended_actions) or "  - 无"
    return "\n".join(
        [
            report.title,
            f"- 影响面: {report.impact}",
            f"- 可能根因: {report.likely_root_cause}",
            f"- 置信度: {report.confidence}",
            "- 证据:",
            evidence,
            "- 建议动作:",
            actions,
        ]
    )


def _scenario_guidance(user_request: str, memory_summary: str) -> tuple[str, list[str]]:
    text = f"{user_request}\n{memory_summary}".lower()
    if any(keyword in text for keyword in ["payment", "支付", "checkout"]):
        return (
            "支付超时可能与 payment-service 连接池耗尽、risk-service 下游延迟、"
            "支付回调或重试放大有关。",
            [
                "检查 order-service 到 payment-service 的 p95/p99 延迟和超时率。",
                "检查 payment-service 连接池使用率、错误率和重试次数。",
                "检查 risk-service 依赖延迟，确认是否拖慢支付校验链路。",
                "核对最近支付相关配置、证书、DNS 或 provider API 变更。",
            ],
        )
    if any(keyword in text for keyword in ["redis", "session", "会话", "ttl"]):
        return (
            "会话查询超时可能与 redis-session 内存压力、慢查询、TTL 不一致、"
            "故障切换或缓存 key 前缀变更有关。",
            [
                "检查 redis-session p95/p99 延迟、CPU、内存和 eviction 指标。",
                "检查 session TTL 分布和近期客户端版本变更。",
                "确认是否发生 Redis failover、复制延迟或热点 key。",
                "抽样 user-center/auth-service 日志，确认 session lookup 失败模式。",
            ],
        )
    return (
        "Token Expired 可能与 auth-service 密钥轮换、JWKS 缓存、issuer 配置或网关时钟偏移有关。",
        [
            "检查 auth-service 当前签名 key id 与 JWKS 发布状态。",
            "刷新 user-center 和 api-gateway 的 JWKS 缓存。",
            "校验 api-gateway 与 auth-service 的 NTP 偏移。",
            "观察 401 与 Token Expired 指标是否回落。",
        ],
    )
