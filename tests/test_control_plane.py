from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agents.graph_builder import build_graph  # noqa: E402
from core.config import load_model_settings  # noqa: E402
from core.contracts import AgentHandoffCommand  # noqa: E402
from prompts.loader import PROMPTS  # noqa: E402
from telemetry.recorder import RunRecorder, summarize_latest_runs  # noqa: E402


def _initial_state() -> dict:
    return {
        "messages": [HumanMessage(content="排查用户中心 Token Expired 报错")],
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


class ControlPlaneTest(unittest.TestCase):
    def test_graph_reaches_finish(self) -> None:
        final_state = build_graph().invoke(_initial_state())

        self.assertEqual(final_state["current_phase"], "finished")
        self.assertTrue(final_state["final_report"])

    def test_handoff_trace_order(self) -> None:
        final_state = build_graph().invoke(_initial_state())

        self.assertEqual(
            [item["to"] for item in final_state["handoff_trace"]],
            ["Topology_Node", "Log_Node", "Metrics_Node", "Memory_Node", "FINISH"],
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

    def test_topology_and_memory_are_real_mock_retrievals(self) -> None:
        final_state = build_graph().invoke(_initial_state())

        self.assertIn("服务 user-center", final_state["impact_summary"])
        self.assertIn("TokenExpiredError", final_state["log_summary"])
        self.assertIn("token_expired_count", final_state["metrics_summary"])
        self.assertIn("INC-2026", final_state["memory_summary"])

    def test_fix_execution_path_is_optional(self) -> None:
        state = _initial_state()
        state["enable_fix_execution"] = True

        final_state = build_graph().invoke(state)

        self.assertEqual(
            [item["to"] for item in final_state["handoff_trace"]],
            ["Topology_Node", "Log_Node", "Metrics_Node", "Memory_Node", "Execute_Fix_Node"],
        )
        self.assertTrue(final_state["fix_execution_result"])

    def test_model_settings_load_from_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv = Path(tmpdir) / ".env"
            dotenv.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "INCIDENT_SUPERVISOR_MODEL=test-supervisor",
                        "INCIDENT_FALLBACK_MODEL=test-fallback",
                        "INCIDENT_EMBEDDING_PROVIDER=fastembed",
                        "INCIDENT_RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5",
                        "INCIDENT_MEMORY_PROVIDER=bm25",
                        "INCIDENT_ENABLE_LLM_ROUTING=true",
                        "INCIDENT_ENABLE_LLM_REPORT=true",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_model_settings(dotenv_path=dotenv)

        self.assertEqual(settings.supervisor_model, "test-supervisor")
        self.assertEqual(settings.fallback_model, "test-fallback")
        self.assertEqual(settings.embedding_provider, "fastembed")
        self.assertEqual(settings.rag_embedding_model, "BAAI/bge-small-zh-v1.5")
        self.assertEqual(settings.memory_provider, "bm25")
        self.assertTrue(settings.enable_llm_routing)
        self.assertTrue(settings.enable_llm_report)
        self.assertTrue(settings.has_openai_credentials)

    def test_prompt_registry_renders_templates(self) -> None:
        supervisor_prompt = PROMPTS.pair(
            "supervisor_system_v1.md",
            "supervisor_user_v1.md",
            user_request="排查用户中心 Token Expired 报错",
            impact_summary="",
            log_summary="",
            metrics_summary="",
            memory_summary="",
            enable_fix_execution="False",
            fix_execution_result="",
        )
        report_prompt = PROMPTS.pair(
            "report_system_v1.md",
            "report_user_v1.md",
            user_request="排查用户中心 Token Expired 报错",
            impact_summary="服务 user-center",
            log_summary="TokenExpiredError",
            metrics_summary="token_expired_count",
            memory_summary="INC-2026-0001",
            fix_plan="",
            fix_execution_result="",
            operator_feedback="",
        )

        self.assertIn("next_worker", supervisor_prompt.system)
        self.assertIn("排查用户中心", supervisor_prompt.user)
        self.assertIn("likely_root_cause", report_prompt.system + report_prompt.user)
        self.assertIn("服务 user-center", report_prompt.user)

    def test_run_recorder_persists_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "runs.sqlite3"
            state = _initial_state()
            state["current_phase"] = "finished"
            state["final_report"] = "done"
            state["handoff_trace"] = [{"to": "FINISH"}]
            recorder = RunRecorder(run_id="test-run", query="query", db_path=db_path)
            recorder.record_event("received", state)
            recorder.finish(state)

            rows = summarize_latest_runs(db_path=db_path, limit=1)
            with sqlite3.connect(db_path) as conn:
                event_count = conn.execute(
                    "SELECT COUNT(*) FROM run_events WHERE run_id = ?",
                    ("test-run",),
                ).fetchone()[0]

        self.assertEqual(rows[0]["run_id"], "test-run")
        self.assertEqual(rows[0]["status"], "finished")
        self.assertEqual(rows[0]["route"], "FINISH")
        self.assertEqual(event_count, 1)


if __name__ == "__main__":
    unittest.main()
