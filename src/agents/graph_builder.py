"""LangGraph control-plane skeleton for incident diagnostics."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from core.contracts import AgentHandoffCommand
from core.state import EngineState

SUPERVISOR = "Supervisor"
TOPOLOGY_NODE = "Topology_Node"
MEMORY_NODE = "Memory_Node"
FINISH = "FINISH"


def _latest_user_request(state: EngineState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return _message_text(message)
    return ""


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


def _fallback_handoff(state: EngineState) -> AgentHandoffCommand:
    if not state.get("impact_summary"):
        return AgentHandoffCommand(
            reasoning="需要先了解受影响服务及其上下游依赖。",
            next_worker=TOPOLOGY_NODE,
            instruction="查询故障相关服务的依赖拓扑，识别可能传播路径。",
        )
    if not state.get("memory_summary"):
        return AgentHandoffCommand(
            reasoning="已有拓扑信息，下一步需要比对历史工单和相似故障。",
            next_worker=MEMORY_NODE,
            instruction="检索历史工单摘要，提取相似告警、修复动作和根因线索。",
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
    if state.get("impact_summary") and not state.get("memory_summary"):
        if handoff.next_worker != MEMORY_NODE:
            return AgentHandoffCommand(
                reasoning=(
                    "Supervisor 输出已通过契约校验，但控制面仍缺少历史记忆；"
                    "按阶段守卫改派 Memory_Node。"
                ),
                next_worker=MEMORY_NODE,
                instruction="检索相似历史工单，提取复盘线索。",
            )
    return handoff


def _llm_handoff(state: EngineState) -> AgentHandoffCommand:
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        temperature=0,
    ).with_structured_output(AgentHandoffCommand)
    user_request = _latest_user_request(state)
    response = llm.invoke(
        [
            (
                "system",
                "你是微服务故障诊断控制面的 Supervisor。"
                "你只能在 Topology_Node、Memory_Node、FINISH 中选择下一步。"
                "如果 impact_summary 和 memory_summary 都已经存在，应选择 FINISH。",
            ),
            (
                "human",
                "用户请求: "
                f"{user_request}\n"
                f"impact_summary: {state.get('impact_summary', '')}\n"
                f"memory_summary: {state.get('memory_summary', '')}",
            ),
        ]
    )
    if not isinstance(response, AgentHandoffCommand):
        return AgentHandoffCommand.model_validate(response)
    return response


def supervisor_node(state: EngineState) -> Command:
    """Route the graph by producing a structured handoff command."""

    routing_errors: list[str] = []
    try:
        handoff = _llm_handoff(state) if os.getenv("OPENAI_API_KEY") else _fallback_handoff(state)
    except Exception as exc:
        routing_errors.append(f"{type(exc).__name__}: {exc}")
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
    """Mock topology worker."""

    impact_summary = (
        "Mock 拓扑影响面: user-center 受 api-gateway 与 web-console 调用；"
        "下游依赖 auth-service、redis-session、mysql-user；"
        "当前疑似传播链路为 user-center -> auth-service。"
    )
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "topology_lookup",
            "impact_summary": impact_summary,
            "messages": [
                AIMessage(
                    name=TOPOLOGY_NODE,
                    content=f"[Mock] 正在查询图谱...\n{impact_summary}",
                )
            ],
        },
    )


def memory_node(state: EngineState) -> Command:
    """Mock memory worker."""

    memory_summary = (
        "Mock 历史记忆: INC-2026-0412 曾出现 auth-service 密钥轮换后 "
        "Token Expired 激增；当时通过回滚签名密钥集合并刷新 JWKS 缓存恢复。"
        "推荐检查 auth-service key rotation、JWKS cache TTL、gateway clock skew。"
    )
    return Command(
        goto=SUPERVISOR,
        update={
            "current_phase": "memory_lookup",
            "memory_summary": memory_summary,
            "messages": [
                AIMessage(
                    name=MEMORY_NODE,
                    content=f"[Mock] 正在查询记忆...\n{memory_summary}",
                )
            ],
        },
    )


def finish_node(state: EngineState) -> dict[str, Any]:
    """Generate a deterministic Sprint 1 report from mocked context."""

    report = "\n".join(
        [
            "诊断报告 V1.0",
            f"- 用户请求: {_latest_user_request(state)}",
            f"- 拓扑影响面: {state.get('impact_summary', 'unknown')}",
            f"- 历史记忆: {state.get('memory_summary', 'none')}",
            "- 初步判断: Token Expired 可能与 auth-service 密钥轮换、JWKS 缓存或网关时钟偏移有关。",
            "- 建议动作: 检查 auth-service 当前签名密钥版本，刷新 user-center/JWKS 缓存，校验 api-gateway 与 auth-service 的 NTP 偏移。",
        ]
    )
    return {
        "current_phase": "finished",
        "final_report": report,
        "messages": [AIMessage(content=report, name=FINISH)],
    }


def build_graph():
    graph = StateGraph(EngineState)
    graph.add_node(SUPERVISOR, supervisor_node)
    graph.add_node(TOPOLOGY_NODE, topology_node)
    graph.add_node(MEMORY_NODE, memory_node)
    graph.add_node(FINISH, finish_node)
    graph.set_entry_point(SUPERVISOR)
    graph.add_edge(FINISH, END)
    return graph.compile()
