"""Report generation strategies for the diagnostic harness."""

from __future__ import annotations

from typing import Protocol

from core.contracts import DiagnosticReport
from core.messages import latest_user_request
from core.model_factory import ModelFactory
from core.state import EngineState


class ReportGenerator(Protocol):
    def generate(self, state: EngineState) -> DiagnosticReport:
        """Build a structured diagnostic report from engine state."""


class TemplateReportGenerator:
    """Deterministic report generator used for offline and fallback mode."""

    def generate(self, state: EngineState) -> DiagnosticReport:
        fix_result = state.get("fix_execution_result") or "未执行"
        return DiagnosticReport(
            title="微服务故障诊断报告",
            impact=state.get("impact_summary") or "未获取拓扑影响面。",
            likely_root_cause=(
                "Token Expired 可能与 auth-service 密钥轮换、JWKS 缓存、"
                "issuer 配置或网关时钟偏移有关。"
            ),
            evidence=[
                f"用户请求: {latest_user_request(state.get('messages', []))}",
                f"历史记忆: {state.get('memory_summary') or '未检索到历史记忆。'}",
                f"模拟执行结果: {fix_result}",
                f"人工反馈: {state.get('operator_feedback') or '无'}",
            ],
            recommended_actions=[
                "检查 auth-service 当前签名 key id 与 JWKS 发布状态。",
                "刷新 user-center 和 api-gateway 的 JWKS 缓存。",
                "校验 api-gateway 与 auth-service 的 NTP 偏移。",
                "观察 401 与 Token Expired 指标是否回落。",
            ],
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
            response = llm.invoke(
                [
                    (
                        "system",
                        "你是资深微服务故障复盘专家。"
                        "必须只输出 JSON，不要输出 Markdown。"
                        "JSON 顶层只能包含以下字段: "
                        "title, impact, likely_root_cause, evidence, recommended_actions, confidence。"
                        "title、impact、likely_root_cause 必须是字符串。"
                        "evidence 和 recommended_actions 必须是字符串数组。"
                        "confidence 只能是 low、medium、high。"
                        "不要输出 diagnosis、topology、recommendations、similar_incidents、timeline 等额外字段。",
                    ),
                    (
                        "human",
                        "\n".join(
                            [
                                "请严格按此示例结构输出:",
                                '{"title":"...","impact":"...","likely_root_cause":"...",'
                                '"evidence":["..."],"recommended_actions":["..."],"confidence":"medium"}',
                                f"用户请求: {latest_user_request(state.get('messages', []))}",
                                f"拓扑影响面: {state.get('impact_summary', '')}",
                                f"历史记忆: {state.get('memory_summary', '')}",
                                f"修复计划: {state.get('fix_plan', '')}",
                                f"执行结果: {state.get('fix_execution_result', '')}",
                                f"人工反馈: {state.get('operator_feedback', '')}",
                            ]
                        ),
                    ),
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
