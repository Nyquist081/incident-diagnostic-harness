from __future__ import annotations

import sys
import unittest
from pathlib import Path

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agents.graph_builder import build_graph  # noqa: E402
from core.contracts import AgentHandoffCommand  # noqa: E402


def _initial_state() -> dict:
    return {
        "messages": [HumanMessage(content="排查用户中心 Token Expired 报错")],
        "current_phase": "received",
        "impact_summary": "",
        "memory_summary": "",
        "final_report": "",
        "handoff_trace": [],
        "routing_errors": [],
    }


class ControlPlaneTest(unittest.TestCase):
    def test_graph_reaches_finish(self) -> None:
        final_state = build_graph().invoke(_initial_state())

        self.assertEqual(final_state["current_phase"], "finished")
        self.assertTrue(final_state["final_report"])

    def test_handoff_trace_order(self) -> None:
        final_state = build_graph().invoke(_initial_state())

        self.assertEqual(
            [item["to"] for item in final_state["handoff_trace"]],
            ["Topology_Node", "Memory_Node", "FINISH"],
        )

    def test_contract_rejects_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AgentHandoffCommand.model_validate(
                {
                    "reasoning": "route",
                    "next_worker": "FINISH",
                    "instruction": "finish",
                    "unexpected": "blocked",
                }
            )

    def test_no_conditional_edges_pattern(self) -> None:
        graph_builder = ROOT / "src" / "agents" / "graph_builder.py"

        self.assertNotIn("add_conditional_edges", graph_builder.read_text())


if __name__ == "__main__":
    unittest.main()
