"""Reusable execution helpers shared by CLI and API entrypoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Iterator, TypeVar
from uuid import uuid4

from langchain_core.messages import HumanMessage

from agents.graph_builder import build_graph
from core.state import EngineState
from telemetry.recorder import RunRecorder

T = TypeVar("T")


def _next_or_none(iterator: Iterator[T]) -> T | None:
    try:
        return next(iterator)
    except StopIteration:
        return None


def initial_state(user_input: str, *, enable_fix_execution: bool = False) -> EngineState:
    return {
        "messages": [HumanMessage(content=user_input)],
        "current_phase": "received",
        "impact_summary": "",
        "log_summary": "",
        "metrics_summary": "",
        "memory_summary": "",
        "fix_plan": "",
        "fix_execution_result": "",
        "enable_fix_execution": enable_fix_execution,
        "operator_feedback": "",
        "final_report": "",
        "handoff_trace": [],
        "routing_errors": [],
        "report_errors": [],
    }


@dataclass(frozen=True)
class DiagnosticResult:
    run_id: str
    final_state: EngineState


@dataclass(frozen=True)
class DiagnosticStep:
    run_id: str
    phase: str
    state: EngineState


class DiagnosticRunner:
    """Thin harness runtime facade for non-interactive diagnostic execution."""

    def run(self, query: str, *, enable_fix_execution: bool = False) -> DiagnosticResult:
        run_id = str(uuid4())
        state = initial_state(query, enable_fix_execution=enable_fix_execution)
        recorder = RunRecorder(run_id=run_id, query=query)
        recorder.record_event("received", state)
        final_state = state
        for step in build_graph().stream(state, stream_mode="values"):
            final_state = step
            recorder.record_event(step.get("current_phase", "unknown"), step)
        recorder.finish(final_state)
        return DiagnosticResult(run_id=run_id, final_state=final_state)

    async def arun(
        self,
        query: str,
        *,
        enable_fix_execution: bool = False,
    ) -> DiagnosticResult:
        return await asyncio.to_thread(
            self.run,
            query,
            enable_fix_execution=enable_fix_execution,
        )

    def stream(self, query: str, *, enable_fix_execution: bool = False) -> Iterator[DiagnosticStep]:
        run_id = str(uuid4())
        state = initial_state(query, enable_fix_execution=enable_fix_execution)
        recorder = RunRecorder(run_id=run_id, query=query)
        recorder.record_event("received", state)
        yield DiagnosticStep(run_id=run_id, phase="received", state=state)
        final_state = state
        for step in build_graph().stream(state, stream_mode="values"):
            final_state = step
            phase = step.get("current_phase", "unknown")
            recorder.record_event(phase, step)
            yield DiagnosticStep(run_id=run_id, phase=phase, state=step)
        recorder.finish(final_state)

    async def astream(
        self,
        query: str,
        *,
        enable_fix_execution: bool = False,
    ) -> AsyncIterator[DiagnosticStep]:
        iterator = self.stream(query, enable_fix_execution=enable_fix_execution)
        while True:
            step = await asyncio.to_thread(_next_or_none, iterator)
            if step is None:
                break
            yield step
