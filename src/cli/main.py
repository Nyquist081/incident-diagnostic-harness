"""Rich-powered CLI entrypoint for the incident diagnostic harness."""

from __future__ import annotations

import argparse
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel

from agents.graph_builder import build_graph
from core.config import load_model_settings
from core.state import EngineState

console = Console()


def _initial_state(user_input: str) -> EngineState:
    return {
        "messages": [HumanMessage(content=user_input)],
        "current_phase": "received",
        "impact_summary": "",
        "log_summary": "",
        "metrics_summary": "",
        "memory_summary": "",
        "fix_plan": "",
        "fix_execution_result": "",
        "enable_fix_execution": False,
        "operator_feedback": "",
        "final_report": "",
        "handoff_trace": [],
        "routing_errors": [],
        "report_errors": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Incident Diagnostic Harness V1.0")
    parser.add_argument("query", nargs="*", help="Plain-text incident description.")
    parser.add_argument(
        "--human-in-loop",
        action="store_true",
        help="Pause before the simulated fix execution node for operator approval.",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Print model role configuration before running the graph.",
    )
    args = parser.parse_args()

    user_input = " ".join(args.query).strip()
    if not user_input:
        user_input = console.input("[bold]请输入故障描述:[/bold] ").strip()

    console.print(
        Panel.fit(
            user_input,
            title="Incident Diagnostic Harness V1.0",
            subtitle="Control Plane",
            border_style="cyan",
        )
    )
    if args.show_config:
        settings = load_model_settings()
        console.print(
            Panel(
                "\n".join(
                    [
                        f"llm routing: {settings.enable_llm_routing}",
                        f"primary model: {settings.primary_model}",
                        f"supervisor model: {settings.supervisor_model}",
                        f"fallback model: {settings.fallback_model}",
                        f"report model: {settings.report_model}",
                        f"llm report: {settings.enable_llm_report}",
                        f"memory provider: {settings.memory_provider}",
                        f"embedding provider: {settings.embedding_provider}",
                        f"rag embedding model: {settings.rag_embedding_model}",
                        f"deepseek thinking: {settings.deepseek_thinking}",
                        f"base url configured: {bool(settings.openai_base_url)}",
                        f"api key configured: {settings.has_openai_credentials}",
                    ]
                ),
                title="Model Config",
                border_style="magenta",
            )
        )

    app = build_graph(interrupt_before_fix=args.human_in_loop)
    state = _initial_state(user_input)
    state["enable_fix_execution"] = args.human_in_loop
    final_state = state
    printed_messages = 1
    config = {"configurable": {"thread_id": str(uuid4())}} if args.human_in_loop else None

    for step in app.stream(state, config=config, stream_mode="values"):
        final_state = step
        phase = step.get("current_phase", "unknown")
        console.print(Panel.fit(f"当前阶段: {phase}", title="Route Step", border_style="blue"))
        messages = step.get("messages", [])
        for message in messages[printed_messages:]:
            if isinstance(message, AIMessage):
                content = str(message.content)
                if content.startswith("[Supervisor]") or content.startswith("[Tool]"):
                    console.print(content.splitlines()[0])
        printed_messages = len(messages)

    if args.human_in_loop and _is_waiting_for_fix(final_state):
        console.print(
            Panel(
                "即将进入 Execute_Fix_Node 模拟修复执行。是否允许继续？",
                title="Human Approval",
                border_style="yellow",
            )
        )
        answer = console.input("[bold yellow]Approve simulated fix execution? [y/N]: [/bold yellow]")
        if answer.strip().lower() == "y":
            for step in app.stream(Command(resume=True), config=config, stream_mode="values"):
                final_state = step
                phase = step.get("current_phase", "unknown")
                console.print(Panel.fit(f"当前阶段: {phase}", title="Route Step", border_style="blue"))
        else:
            feedback = console.input("[bold]拒绝原因或调整建议:[/bold] ").strip()
            continuation_state = {
                **final_state,
                "enable_fix_execution": False,
                "operator_feedback": feedback or "Operator rejected simulated fix execution.",
            }
            final_state = build_graph().invoke(continuation_state)

    if final_state.get("routing_errors"):
        console.print(
            Panel(
                "\n".join(final_state["routing_errors"]),
                title="Routing Fallbacks",
                border_style="yellow",
            )
        )
    if final_state.get("report_errors"):
        console.print(
            Panel(
                "\n".join(final_state["report_errors"]),
                title="Report Fallbacks",
                border_style="yellow",
            )
        )

    console.print(
        Panel(
            final_state.get("final_report", "未生成报告"),
            title="Final Report",
            border_style="green",
        )
    )


def _is_waiting_for_fix(state: EngineState) -> bool:
    trace = state.get("handoff_trace", [])
    if not trace:
        return False
    return trace[-1].get("to") == "Execute_Fix_Node" and not state.get("fix_execution_result")


if __name__ == "__main__":
    main()
