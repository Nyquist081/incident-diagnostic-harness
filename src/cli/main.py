"""Rich-powered CLI entrypoint for the incident diagnostic harness."""

from __future__ import annotations

import argparse

from langchain_core.messages import AIMessage, HumanMessage
from rich.console import Console
from rich.panel import Panel

from agents.graph_builder import build_graph
from core.state import EngineState

console = Console()


def _initial_state(user_input: str) -> EngineState:
    return {
        "messages": [HumanMessage(content=user_input)],
        "current_phase": "received",
        "impact_summary": "",
        "memory_summary": "",
        "final_report": "",
        "handoff_trace": [],
        "routing_errors": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Incident Diagnostic Harness V1.0")
    parser.add_argument("query", nargs="*", help="Plain-text incident description.")
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

    app = build_graph()
    state = _initial_state(user_input)
    final_state = state
    printed_messages = 1

    for step in app.stream(state, stream_mode="values"):
        final_state = step
        phase = step.get("current_phase", "unknown")
        console.print(Panel.fit(f"当前阶段: {phase}", title="Route Step", border_style="blue"))
        messages = step.get("messages", [])
        for message in messages[printed_messages:]:
            if isinstance(message, AIMessage):
                content = str(message.content)
                if content.startswith("[Supervisor]") or content.startswith("[Mock]"):
                    console.print(content.splitlines()[0])
        printed_messages = len(messages)

    if final_state.get("routing_errors"):
        console.print(
            Panel(
                "\n".join(final_state["routing_errors"]),
                title="Routing Fallbacks",
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


if __name__ == "__main__":
    main()
