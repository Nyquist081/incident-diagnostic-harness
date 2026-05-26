from __future__ import annotations

import sys
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agents.graph_builder import build_graph  # noqa: E402

CASES = [
    "排查用户中心 Token Expired 报错",
    "用户中心登录后立刻提示 token expired",
    "api-gateway 到 user-center 出现 401 激增",
    "鉴权中心 key rotation 后 JWT kid not found",
    "redis session 查询超时导致登录失败",
    "订单 checkout 支付超时",
    "payment-service 风控校验超时",
    "库存服务返回 stale stock count",
    "用户库查询 p99 延迟升高",
    "SSO 企业租户出现 Token Expired",
]


def _initial_state(query: str) -> dict:
    return {
        "messages": [HumanMessage(content=query)],
        "current_phase": "received",
        "impact_summary": "",
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


def _estimate_tokens(text: str) -> int:
    # Lightweight offline estimate: English tokens plus rough CJK character cost.
    cjk_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    ascii_chunks = len([chunk for chunk in text.replace("\n", " ").split(" ") if chunk])
    return cjk_chars + ascii_chunks


def main() -> None:
    console = Console()
    graph = build_graph()
    table = Table(title="Incident Harness Benchmark")
    table.add_column("Case", justify="right")
    table.add_column("Query")
    table.add_column("Route")
    table.add_column("Latency ms", justify="right")
    table.add_column("Token Est.", justify="right")
    table.add_column("Fallbacks", justify="right")

    for index, query in enumerate(CASES, start=1):
        started = time.perf_counter()
        final_state = graph.invoke(_initial_state(query))
        elapsed_ms = (time.perf_counter() - started) * 1000
        route = " -> ".join(item["to"] for item in final_state["handoff_trace"])
        token_estimate = _estimate_tokens(
            "\n".join(
                [
                    query,
                    final_state.get("impact_summary", ""),
                    final_state.get("memory_summary", ""),
                    final_state.get("final_report", ""),
                ]
            )
        )
        table.add_row(
            str(index),
            query,
            route,
            f"{elapsed_ms:.1f}",
            str(token_estimate),
            str(len(final_state.get("routing_errors", []))),
        )

    console.print(table)


if __name__ == "__main__":
    main()
