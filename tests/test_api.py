from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from api.main import app  # noqa: E402


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_diagnose_endpoint_returns_report(self) -> None:
        response = self.client.post(
            "/diagnose",
            json={"query": "排查用户中心 Token Expired 报错"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current_phase"], "finished")
        self.assertTrue(payload["run_id"])
        self.assertTrue(payload["final_report"])
        self.assertEqual(
            payload["route"],
            ["Topology_Node", "Log_Node", "Metrics_Node", "Memory_Node", "FINISH"],
        )

    def test_rejects_unknown_request_fields(self) -> None:
        response = self.client.post(
            "/diagnose",
            json={
                "query": "排查用户中心 Token Expired 报错",
                "unexpected": "blocked",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_stream_endpoint_returns_ndjson_events(self) -> None:
        with self.client.stream(
            "POST",
            "/diagnose/stream",
            json={"query": "排查用户中心 Token Expired 报错"},
        ) as response:
            lines = [line for line in response.iter_lines() if line]

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(lines), 1)
        self.assertIn('"phase": "received"', lines[0])
        self.assertIn('"phase": "finished"', lines[-1])

    def test_runs_endpoint_lists_recent_runs(self) -> None:
        response = self.client.get("/runs?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertIn("runs", response.json())


if __name__ == "__main__":
    unittest.main()
