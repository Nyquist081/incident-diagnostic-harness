"""LangGraph control-plane skeleton for incident diagnostics."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from context.strategy import DiagnosticContextStrategy
from core.contracts import AgentHandoffCommand
from core.messages import latest_user_request
from core.model_factory import ModelFactory
from core.paths import MOCK_DATA_DIR
from core.state import EngineState
from prompts.loader import PROMPTS
from reporting.generator import LLMReportGenerator, render_report
from tools.json_store import JsonStore
from tools.logs import MockLogProvider
from tools.memory import build_memory_provider
from tools.metrics import MockMetricsProvider
from tools.topology import TopologyTool

SUPERVISOR = "Supervisor"
TOPOLOGY_NODE = "Topology_Node"
LOG_NODE = "Log_Node"
METRICS_NODE = "Metrics_Node"
MEMORY_NODE = "Memory_Node"
EXECUTE_FIX_NODE = "Execute_Fix_Node"
FINISH = "FINISH"


STORE = JsonStore(MOCK_DATA_DIR)
CONTEXT_STRATEGY = DiagnosticContextStrategy()
TOPOLOGY_TOOL = TopologyTool(STORE.load("topology.json"))
LOG_TOOL = MockLogProvider(STORE.load("logs.json"))
METRICS_TOOL = MockMetricsProvider(STORE.load("metrics.json"))
MODEL_FACTORY = ModelFactory()
MEMORY_TOOL = build_memory_provider(
    STORE.load("incidents.json"),
    provider=MODEL_FACTORY.settings.memory_provider,
    embedding_model=MODEL_FACTORY.settings.rag_embedding_model,
)
REPORT_GENERATOR = LLMReportGenerator(MODEL_FACTORY)


def _fallback_handoff(state: EngineState) -> AgentHandoffCommand:
    if not state.get("impact_summary"):
        return AgentHandoffCommand(
            reasoning="需要先了解受影响服务及其上下游依赖。",
            next_worker=TOPOLOGY_NODE,
            instruction="查询故障相关服务的依赖拓扑，识别可能传播路径。",
        )
    if not state.get("log_summary"):
        return AgentHandoffCommand(
            reasoning="已有拓扑信息，下一步需要查询当前故障窗口的日志证据。",
            next_worker=LOG_NODE,
            instruction="检索相关服务近期错误日志，提取错误模式、trace id 和关键异常。",
        )
    if not state.get("metrics_summary"):
        return AgentHandoffCommand(
            reasoning="已有日志证据，下一步需要查询指标确认故障强度和异常维度。",
            next_worker=METRICS_NODE,
            instruction="检索相关服务指标，提取错误率、延迟、资源使用率和基线偏离。",
        )
    if not state.get("memory_summary"):
        return AgentHandoffCommand(
            reasoning="已有当前观测证据，下一步需要比对历史工单和相似故障。",
            next_worker=MEMORY_NODE,
            instruction="检索历史工单摘要，提取相似告警、修复动作和根因线索。",
        )
    if state.get("enable_fix_execution") and not state.get("fix_execution_result"):
        return AgentHandoffCommand(
            reasoning="诊断证据已齐备，进入人工确认前的模拟修复执行阶段。",
            next_worker=EXECUTE_FIX_NODE,
            instruction="生成并等待执行模拟修复动作，执行前必须经过人类确认。",
        )
    return AgentHandoffCommand(
        reasoning="拓扑和历史记忆均已收集，可以收敛诊断报告。",
        next_worker=FINISH,
        instruction="汇总控制面上下文，生成最终诊断报告。",
    )


def _enforce_phase_guard(state: EngineState, handoff: AgentHandoffCommand) -> AgentHandoffCommand:
    """Keep the Sprint 1 graph deterministic even if the LLM routes too early."""

    if not state.get("impact_summary") and handoff.next_worker != TOPOLOGY_NODE:
        return AgentHandoffCommand(
            reasoning=(
                "Supervisor 输出已通过契约校验，但控制面仍缺少拓扑影响面；"
                "按阶段守卫改派 Topology_Node。"
            ),
            next_worker=TOPOLOGY_NODE,
            instruction="先获取受影响服务的依赖拓扑和传播路径。",
        )
    if state.get("impact_summary") and not state.get("log_summary"):
        if handoff.next_worker != LOG_NODE:
            return AgentHandoffCommand(
                reasoning=(
                    "Supervisor 输出已通过契约校验，但控制面仍缺少日志证据；"
                    "按阶段守卫改派 Log_Node。"
                ),
                next_worker=LOG_NODE,
                instruction="检索当前故障窗口日志，提取异常模式。",
            )
    if state.get("log_summary") and not state.get("metrics_summary"):
        if handoff.next_worker != METRICS_NODE:
            return AgentHandoffCommand(
                reasoning=(
                    "Supervisor 输出已通过契约校验，但控制面仍缺少指标证据；"
                    "按阶段守卫改派 Metrics_Node。"
                ),
                next_worker=METRICS_NODE,
                instruction="检索当前故障窗口指标，提取基线偏离。",
            )
    if state.get("metrics_summary") and not state.get("memory_summary"):
        if handoff.next_worker != MEMORY_NODE:
            return AgentHandoffCommand(
                reasoning=(
                    "Supervisor 输出已通过契约校验，但控制面仍缺少历史记忆；"
                    "按阶段守卫改派 Memory_Node。"
                ),
                next_worker=MEMORY_NODE,
                instruction="检索相似历史工单，提取复盘线索。",
            )
    if state.get("enable_fix_execution") and state.get("memory_summary"):
        if not state.get("fix_execution_result") and handoff.next_worker == FINISH:
            return AgentHandoffCommand(
                reasoning=(
                    "已启用人类在环修复执行，但尚未产生执行结果；"
                    "按阶段守卫改派 Execute_Fix_Node。"
                ),
                next_worker=EXECUTE_FIX_NODE,
                instruction="准备模拟修复动作，等待人类确认后执行。",
            )
    return handoff


def _invoke_structured_handoff(state: EngineState, model_name: str) -> AgentHandoffCommand:
    llm = MODEL_FACTORY.chat(model_name).with_structured_output(
        AgentHandoffCommand,
        method="json_mode",
    )
    user_request = latest_user_request(state.get("messages", []))
    prompt = PROMPTS.pair(
        "supervisor_system_v1.md",
        "supervisor_user_v1.md",
        user_request=user_request,
        impact_summary=state.get("impact_summary", ""),
        log_summary=state.get("log_summary", ""),
        metrics_summary=state.get("metrics_summary", ""),
        memory_summary=state.get("memory_summary", ""),
        enable_fix_execution=str(state.get("enable_fix_execution", False)),
        fix_execution_result=state.get("fix_execution_result", ""),
    )
    response = llm.invoke(
        [
            ("system", prompt.system),
            ("human", prompt.user),
        ]
    )
    if not isinstance(response, AgentHandoffCommand):
        return AgentHandoffCommand.model_validate(response)
    return response


def _llm_handoff(state: EngineState) -> AgentHandoffCommand:
    settings = MODEL_FACTORY.settings
    return _invoke_structured_handoff(state, settings.supervisor_model)


def _fallback_llm_handoff(state: EngineState) -> AgentHandoffCommand:
    settings = MODEL_FACTORY.settings
    return _invoke_structured_handoff(state, settings.fallback_model)


def supervisor_node(state: EngineState) -> Command:
    """Route the graph by producing a structured handoff command."""

    routing_errors: list[str] = []
    settings = MODEL_FACTORY.settings
    if settings.has_openai_credentials and settings.enable_llm_routing:
        try:
            handoff = _llm_handoff(state)
        except Exception as exc:
            routing_errors.append(
                f"supervisor_model={settings.supervisor_model} failed: {type(exc).__name__}: {exc}"
            )
            try:
                handoff = _fallback_llm_handoff(state)
            except Exception as fallback_exc:
                routing_errors.append(
                    "fallback_model="
                    f"{settings.fallback_model} failed: "
                    f"{type(fallback_exc).__name__}: {fallback_exc}"
                )
                handoff = _fallback_handoff(state)
    else:
        handoff = _fallback_handoff(state)

    handoff = _enforce_phase_guard(state, handoff)
    return Command(
        goto=handoff.next_worker,
        update={
            "current_phase": "supervisor_routing",
            "messages": [
                AIMessage(
                    content=(
                        f"[Supervisor] -> {handoff.next_worker}: {handoff.reasoning}\n"
                        f"Instruction: {handoff.instruction}"
                    ),
                    name=SUPERVISOR,
                )
            ],
            "handoff_trace": [
                {
                    "from": SUPERVISOR,
                    "to": handoff.next_worker,
                    "reasoning": handoff.reasoning,
                    "instruction": handoff.instruction,
                }
            ],
            "routing_errors": routing_errors,
        },
    )


def topology_node(state: EngineState) -> Command:
    """Topology worker backed by mock graph data."""

    impact = TOPOLOGY_TOOL.lookup(latest_user_request(state.get("messages", [])))
    impact_summary = CONTEXT_STRATEGY.summarize_topology(impact)
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "topology_lookup",
            "impact_summary": impact_summary,
            "messages": [
                AIMessage(
                    name=TOPOLOGY_NODE,
                    content=f"[Tool] 正在查询拓扑图谱...\n{impact_summary}",
                )
            ],
        },
    )


def memory_node(state: EngineState) -> Command:
    """Memory worker backed by local BM25 over mock incidents."""

    query = CONTEXT_STRATEGY.build_memory_query(
        latest_user_request(state.get("messages", [])),
        state.get("impact_summary", ""),
        state.get("log_summary", ""),
        state.get("metrics_summary", ""),
    )
    hits = MEMORY_TOOL.search(query, top_k=3)
    memory_summary = CONTEXT_STRATEGY.summarize_memory(hits)
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "memory_lookup",
            "memory_summary": memory_summary,
            "messages": [
                AIMessage(
                    name=MEMORY_NODE,
                    content=f"[Tool] 正在检索历史记忆...\n{memory_summary}",
                )
            ],
        },
    )


def log_node(state: EngineState) -> Command:
    """Log worker backed by the configured log search provider."""

    query = CONTEXT_STRATEGY.build_observation_query(
        latest_user_request(state.get("messages", [])),
        state.get("impact_summary", ""),
    )
    hits = LOG_TOOL.search(query, top_k=3)
    log_summary = CONTEXT_STRATEGY.summarize_logs(hits)
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "log_lookup",
            "log_summary": log_summary,
            "messages": [
                AIMessage(
                    name=LOG_NODE,
                    content=f"[Tool] 正在检索故障日志...\n{log_summary}",
                )
            ],
        },
    )


def metrics_node(state: EngineState) -> Command:
    """Metrics worker backed by the configured metrics provider."""

    query = CONTEXT_STRATEGY.build_observation_query(
        latest_user_request(state.get("messages", [])),
        state.get("impact_summary", ""),
    )
    points = METRICS_TOOL.search(query, top_k=3)
    metrics_summary = CONTEXT_STRATEGY.summarize_metrics(points)
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "metrics_lookup",
            "metrics_summary": metrics_summary,
            "messages": [
                AIMessage(
                    name=METRICS_NODE,
                    content=f"[Tool] 正在检索故障指标...\n{metrics_summary}",
                )
            ],
        },
    )


def execute_fix_node(state: EngineState) -> Command:
    """Simulated fix execution node, guarded by LangGraph interrupt in HITL mode."""

    plan = (
        "模拟修复计划: 1) 刷新 user-center 与 api-gateway 的 JWKS 缓存；"
        "2) 校验 auth-service 当前签名 key id；3) 检查 gateway 与 auth-service NTP 偏移；"
        "4) 若 key id 不一致，回滚到上一签名密钥集合。"
    )
    result = (
        "模拟执行结果: 已刷新 JWKS 缓存，NTP 偏移在阈值内，发现 auth-service key id "
        "与 user-center 缓存不一致；建议执行密钥集合回滚并观察 401/Token Expired 指标。"
    )
    return Command(
        goto=FINISH,
        update={
            "current_phase": "fix_execution",
            "fix_plan": plan,
            "fix_execution_result": result,
            "messages": [AIMessage(name=EXECUTE_FIX_NODE, content=f"[Execute] {result}")],
        },
    )


def finish_node(state: EngineState) -> dict[str, Any]:
    """Generate a report through the configured report strategy."""

    report_model, report_errors = REPORT_GENERATOR.generate_with_errors(state)
    report = render_report(report_model)
    return {
        "current_phase": "finished",
        "final_report": report,
        "messages": [AIMessage(content=report, name=FINISH)],
        "report_errors": report_errors,
    }


def build_graph(*, interrupt_before_fix: bool = False):
    graph = StateGraph(EngineState)
    graph.add_node(SUPERVISOR, supervisor_node)
    graph.add_node(TOPOLOGY_NODE, topology_node)
    graph.add_node(LOG_NODE, log_node)
    graph.add_node(METRICS_NODE, metrics_node)
    graph.add_node(MEMORY_NODE, memory_node)
    graph.add_node(EXECUTE_FIX_NODE, execute_fix_node)
    graph.add_node(FINISH, finish_node)
    graph.set_entry_point(SUPERVISOR)
    graph.add_edge(FINISH, END)
    interrupt_before = [EXECUTE_FIX_NODE] if interrupt_before_fix else None
    checkpointer = MemorySaver() if interrupt_before_fix else None
    return graph.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
