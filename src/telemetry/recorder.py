"""SQLite-backed run telemetry for diagnostic executions."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from core.messages import message_text
from core.paths import PROJECT_ROOT
from core.state import EngineState

DEFAULT_DB_PATH = PROJECT_ROOT / "runs" / "incident_runs.sqlite3"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _message_to_dict(message: BaseMessage) -> dict[str, Any]:
    return {
        "type": message.type,
        "name": getattr(message, "name", None),
        "content": message_text(message),
    }


def state_snapshot(state: EngineState) -> dict[str, Any]:
    return {
        "current_phase": state.get("current_phase", ""),
        "impact_summary": state.get("impact_summary", ""),
        "log_summary": state.get("log_summary", ""),
        "metrics_summary": state.get("metrics_summary", ""),
        "memory_summary": state.get("memory_summary", ""),
        "fix_plan": state.get("fix_plan", ""),
        "fix_execution_result": state.get("fix_execution_result", ""),
        "enable_fix_execution": state.get("enable_fix_execution", False),
        "operator_feedback": state.get("operator_feedback", ""),
        "final_report": state.get("final_report", ""),
        "handoff_trace": state.get("handoff_trace", []),
        "routing_errors": state.get("routing_errors", []),
        "report_errors": state.get("report_errors", []),
        "messages": [_message_to_dict(message) for message in state.get("messages", [])],
    }


@dataclass
class RunRecorder:
    run_id: str
    query: str
    db_path: Path = DEFAULT_DB_PATH

    def __post_init__(self) -> None:
        self.started_at_ms = _now_ms()
        self._last_event_ms = self.started_at_ms
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._create_run()

    def record_event(self, phase: str, state: EngineState) -> None:
        now = _now_ms()
        latency_ms = now - self._last_event_ms
        self._last_event_ms = now
        snapshot = state_snapshot(state)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO run_events
                    (run_id, ts_ms, phase, latency_ms, snapshot_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.run_id, now, phase, latency_ms, _json_dumps(snapshot)),
            )

    def finish(self, state: EngineState) -> None:
        finished_at_ms = _now_ms()
        total_latency_ms = finished_at_ms - self.started_at_ms
        route = " -> ".join(item["to"] for item in state.get("handoff_trace", []))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE runs
                SET
                    finished_at_ms = ?,
                    total_latency_ms = ?,
                    status = ?,
                    route = ?,
                    final_report = ?,
                    routing_errors_json = ?,
                    report_errors_json = ?,
                    final_state_json = ?
                WHERE run_id = ?
                """,
                (
                    finished_at_ms,
                    total_latency_ms,
                    state.get("current_phase", "unknown"),
                    route,
                    state.get("final_report", ""),
                    _json_dumps(state.get("routing_errors", [])),
                    _json_dumps(state.get("report_errors", [])),
                    _json_dumps(state_snapshot(state)),
                    self.run_id,
                ),
            )

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    started_at_ms INTEGER NOT NULL,
                    finished_at_ms INTEGER,
                    total_latency_ms INTEGER,
                    status TEXT NOT NULL,
                    route TEXT,
                    final_report TEXT,
                    routing_errors_json TEXT NOT NULL,
                    report_errors_json TEXT NOT NULL,
                    final_state_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    ts_ms INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id)"
            )

    def _create_run(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs
                    (run_id, query, started_at_ms, status,
                     routing_errors_json, report_errors_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.run_id,
                    self.query,
                    self.started_at_ms,
                    "running",
                    _json_dumps([]),
                    _json_dumps([]),
                ),
            )


def summarize_latest_runs(db_path: Path = DEFAULT_DB_PATH, *, limit: int = 10) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT run_id, query, status, total_latency_ms, route, started_at_ms
            FROM runs
            ORDER BY started_at_ms DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
