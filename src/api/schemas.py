"""API request and response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DiagnoseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, description="Plain-text incident description.")
    enable_fix_execution: bool = Field(
        default=False,
        description="Allow the simulated fix execution node in non-interactive API mode.",
    )


class HandoffTraceItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    from_: str | None = Field(default=None, alias="from")
    to: str
    reasoning: str = ""
    instruction: str = ""


class DiagnoseResponse(BaseModel):
    run_id: str
    current_phase: str
    final_report: str
    route: list[str]
    handoff_trace: list[HandoffTraceItem]
    impact_summary: str
    log_summary: str
    metrics_summary: str
    memory_summary: str
    fix_plan: str
    fix_execution_result: str
    routing_errors: list[str]
    report_errors: list[str]


class DiagnoseStreamEvent(BaseModel):
    run_id: str
    phase: str
    route: list[str]
    final_report: str = ""
    routing_errors: list[str] = Field(default_factory=list)
    report_errors: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    run_id: str
    query: str
    status: str
    total_latency_ms: int | None = None
    route: str | None = None
    started_at_ms: int


class RunsResponse(BaseModel):
    runs: list[RunSummary]


def state_to_response(run_id: str, state: dict[str, Any]) -> DiagnoseResponse:
    handoff_trace = state.get("handoff_trace", [])
    return DiagnoseResponse(
        run_id=run_id,
        current_phase=state.get("current_phase", ""),
        final_report=state.get("final_report", ""),
        route=[item.get("to", "") for item in handoff_trace],
        handoff_trace=handoff_trace,
        impact_summary=state.get("impact_summary", ""),
        log_summary=state.get("log_summary", ""),
        metrics_summary=state.get("metrics_summary", ""),
        memory_summary=state.get("memory_summary", ""),
        fix_plan=state.get("fix_plan", ""),
        fix_execution_result=state.get("fix_execution_result", ""),
        routing_errors=state.get("routing_errors", []),
        report_errors=state.get("report_errors", []),
    )


def state_to_stream_event(run_id: str, phase: str, state: dict[str, Any]) -> DiagnoseStreamEvent:
    handoff_trace = state.get("handoff_trace", [])
    return DiagnoseStreamEvent(
        run_id=run_id,
        phase=phase,
        route=[item.get("to", "") for item in handoff_trace],
        final_report=state.get("final_report", ""),
        routing_errors=state.get("routing_errors", []),
        report_errors=state.get("report_errors", []),
    )
